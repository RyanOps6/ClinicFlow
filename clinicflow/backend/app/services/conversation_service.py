import json
import re
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.core.constants import BookingState, CancelState, EventType, RescheduleState, UrgencyLevel
from app.models.call_session import CallSession
from app.schemas.session import ExtractionResult, SendMessageResponse
from app.services import ai_assistant_service
from app.services import appointment_service as apt_svc
from app.services import availability_service as avail_svc
from app.services import event_service as evt_svc
from app.services import session_store as store
from app.services import summary_service as summary_svc
from app.services import triage_service as triage_svc
from app.utils import session_memory as mem
from app.utils import text_helpers
from app.utils.slot_utils import match_slot, normalize_natural_slot
from app.utils.field_memory import FieldMemory, PROTECTED_FIELDS

_RESCHEDULE_KEYWORDS = [
    "reschedule", "move my appointment", "change my appointment",
    "shift my appointment", "change appointment time",
    "move appointment", "shift appointment", "reschedule appointment",
    "change my booking", "move my booking",
]


class CorrectionState:
    NONE = "none"
    AWAITING_NAME = "awaiting_name_correction"
    AWAITING_PHONE = "awaiting_phone_correction"
    AWAITING_REASON = "awaiting_reason_correction"
    AWAITING_SLOT = "awaiting_slot_correction"
    AWAITING_INTENT = "awaiting_intent_correction"


def _is_in_correction_flow(session: CallSession) -> bool:
    return mem.get_correction_target(session) is not None


def _build_session_context(session: CallSession) -> dict:
    collected = store.get_collected_data(session)
    return {
        "session_id": session.id,
        "session_type": session.session_type,
        "intent": session.intent,
        "workflow_state": session.workflow_state,
        "active_workflow": session.session_type or "booking",
        "known_info": collected,
        "collected_data": collected,
        "recent_transcript": store.get_transcript(session)[-3:],
    }


def _extract_from_ai(message: str, session: CallSession) -> Optional[ExtractionResult]:
    context = _build_session_context(session)
    return ai_assistant_service.analyze_message(message, context)


def _check_correction_flow(message: str, session: CallSession) -> ExtractionResult | None:
    correction_target = mem.get_correction_target(session)
    if not correction_target:
        return None

    result = ExtractionResult()

    if correction_target == "full_name":
        name = text_helpers.extract_name(message)
        if not name:
            name = text_helpers.extract_name_simple(message)
        if name:
            cleaned_name = name.replace("actually ", "").replace("Actually ", "")
            result.full_name = cleaned_name
            mem.set_field(session, "full_name", cleaned_name)
            mem.confirm_field(session, "full_name")
            mem.clear_correction_target(session)
            return result
    elif correction_target == "phone":
        phone = text_helpers.extract_phone(message)
        if phone:
            result.phone = phone
            mem.set_field(session, "phone", phone)
            mem.confirm_field(session, "phone")
            mem.clear_correction_target(session)
            return result
    elif correction_target == "reason_for_visit":
        reason = text_helpers.extract_reason(message)
        if reason:
            result.reason_for_visit = reason
            mem.set_field(session, "reason_for_visit", reason)
            mem.confirm_field(session, "reason_for_visit")
            mem.clear_correction_target(session)
            return result
    elif correction_target == "preferred_slot_or_date":
        offered = store.get_offered_slots(session)
        if offered:
            slot = match_slot(message, offered)
            if not slot:
                slot = normalize_natural_slot(message)
            if slot:
                result.preferred_slot_or_date = slot
                mem.set_field(session, "preferred_slot_or_date", slot)
                mem.confirm_field(session, "preferred_slot_or_date")
                mem.clear_correction_target(session)
                return result

    return ExtractionResult()


def _maybe_enter_correction_flow(message: str, session: CallSession) -> bool:
    correction_target = mem.detect_correction_target(message, session)
    if correction_target:
        mem.set_correction_target(session, correction_target)
        mem.dispute_field(session, correction_target)
        mem.clear_field(session, correction_target)
        return True
    return False


def _handle_smalltalk_and_queries(message: str, session: CallSession, db: DBSession = None) -> str | None:
    lower = message.lower().strip()
    collected = store.get_collected_data(session)

    if mem.detect_smalltalk(message):
        name = collected.get("full_name", "")
        responses = [
            "I'm ClinicFlow's virtual receptionist. I'm here to help you with appointment scheduling, rescheduling, or cancellations.",
            "I'm the clinic's AI assistant. I can help you book, reschedule, or cancel appointments.",
        ]
        smalltalk = responses[hash(str(session.id)) % len(responses)]
        pending_field = _get_next_missing_field(session)
        if pending_field:
            smalltalk += f" {pending_field}"
        return smalltalk

    if mem.detect_name_query(message):
        name = collected.get("full_name")
        status = mem.get_field_status(session, "full_name")
        if status == "confirmed":
            return f"Your name on file is {name}."
        elif status == "tentative":
            return f"I currently have your name as {name}, but I haven't fully confirmed it yet. Is that correct?"
        else:
            return "I don't have your name on file yet. Could you please tell me your full name?"

    if mem.detect_appointment_query(message):
        # Try to find the appointment from session data first, then DB
        collected = store.get_collected_data(session)
        from app.services import appointment_service as apt_svc
        # Use collected data if available
        if collected.get("phone"):
            appointment = apt_svc.find_upcoming_by_phone(db, collected.get("phone"))
            if appointment:
                slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
                return f"I found your upcoming appointment on {slot}. Reason: {appointment.reason_for_visit or 'General visit'}."
        if collected.get("full_name") and collected.get("phone"):
            appointment = apt_svc.find_existing_appointment_by_name_phone(
                db, collected.get("full_name"), collected.get("phone")
            )
            if appointment:
                slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
                return f"I found your upcoming appointment on {slot}. Reason: {appointment.reason_for_visit or 'General visit'}."
        return "I don't have an appointment on file for you yet. Could you provide your phone number so I can look it up?"

    if mem.detect_state_query(message):
        fields = mem.get_all_tracked_fields(session)
        known = [f"{k}: {v['value']}" for k, v in fields.items() if v["status"] != "missing"]
        if known:
            return "Here's what I have so far: " + ", ".join(known) + "."
        return "I don't have any information recorded yet. How can I help you today?"

    return None


def _get_next_missing_field(session: CallSession) -> str | None:
    collected = store.get_collected_data(session)
    state = session.workflow_state or BookingState.GREETING

    if state == BookingState.GREETING and not collected.get("full_name"):
        return "Could you please tell me your full name?"
    if state in (BookingState.GREETING, BookingState.AWAITING_NAME) and not collected.get("full_name"):
        return "Could you please tell me your full name?"
    if not collected.get("phone"):
        return "What's the best phone number to reach you?"
    if not collected.get("reason_for_visit"):
        return "What's the reason for your visit today?"
    if not collected.get("preferred_slot_or_date"):
        return "Could you select an available slot?"
    return None


def _deterministic_extraction(message: str, session: CallSession) -> ExtractionResult:
    result = ExtractionResult()
    state = session.workflow_state or BookingState.GREETING
    collected = store.get_collected_data(session)

    if state == BookingState.GREETING:
        if not collected.get("full_name"):
            name = text_helpers.extract_name(message)
            if name:
                result.full_name = name
        if not collected.get("reason_for_visit") and not result.reason_for_visit:
            reason = text_helpers.extract_reason(message)
            if reason:
                result.reason_for_visit = reason

    if state == BookingState.AWAITING_NAME:
        if not collected.get("full_name"):
            name = text_helpers.extract_name(message)
            if not name:
                name = text_helpers.extract_name_simple(message)
            if name:
                result.full_name = name
        if not collected.get("reason_for_visit"):
            reason = text_helpers.extract_reason(message)
            if reason:
                result.reason_for_visit = reason

    if state == BookingState.AWAITING_PHONE:
        if not collected.get("phone"):
            phone = text_helpers.extract_phone(message)
            if phone:
                result.phone = phone

    if state == BookingState.AWAITING_REASON:
        if not collected.get("reason_for_visit"):
            reason = text_helpers.extract_reason(message)
            if reason:
                result.reason_for_visit = reason

    if state == BookingState.AWAITING_SLOT_SELECTION:
        offered = store.get_offered_slots(session)
        if offered:
            slot = match_slot(message, offered)
            if slot:
                result.preferred_slot_or_date = slot
            else:
                normalized = normalize_natural_slot(message)
                if normalized:
                    result.preferred_slot_or_date = normalized

    if state == BookingState.AWAITING_CONFIRMATION:
        if text_helpers.is_affirmative(message):
            result.confirmation = True
        elif text_helpers.is_negative(message):
            result.confirmation = False

    return result


def _merge_extraction(session: CallSession, extraction: ExtractionResult):
    updates = {}
    if extraction.full_name:
        updates["full_name"] = extraction.full_name
    if extraction.phone:
        updates["phone"] = extraction.phone
    if extraction.reason_for_visit:
        updates["reason_for_visit"] = extraction.reason_for_visit
    if extraction.preferred_slot_or_date:
        slot = extraction.preferred_slot_or_date
        normalized = normalize_natural_slot(slot) or match_slot(slot, avail_svc.get_available_slots()) or slot
        updates["preferred_slot_or_date"] = normalized
    if extraction.doctor_name:
        updates["doctor_name"] = extraction.doctor_name
    if extraction.insurance_provider:
        updates["insurance_provider"] = extraction.insurance_provider
    if extraction.symptoms:
        existing = store.get_collected_data(session).get("symptoms", [])
        updates["symptoms"] = list(set(existing + extraction.symptoms))
    if extraction.notes:
        updates["notes"] = extraction.notes
    if extraction.confirmation is not None:
        updates["confirmation"] = extraction.confirmation
    if extraction.reason_for_cancellation:
        updates["reason_for_cancellation"] = extraction.reason_for_cancellation
    if extraction.intent:
        session.intent = extraction.intent
    if updates:
        store.update_collected_data(session, updates)


def _safe_merge_extraction(session: CallSession, extraction: ExtractionResult, state: str = None):
    """State-gated merge: only merge fields relevant to the current workflow state."""
    if state is None:
        state = session.workflow_state or BookingState.GREETING

    updates = {}

    # Fields allowed per state
    if state == BookingState.GREETING:
        allowed = {"full_name", "reason_for_visit", "preferred_slot_or_date"}
    elif state == BookingState.AWAITING_NAME:
        allowed = {"full_name", "reason_for_visit", "preferred_slot_or_date"}
    elif state == BookingState.AWAITING_PHONE:
        allowed = {"phone"}
    elif state == BookingState.AWAITING_REASON:
        allowed = {"reason_for_visit"}
    elif state == BookingState.AWAITING_SLOT_SELECTION:
        allowed = {"preferred_slot_or_date"}
    elif state == BookingState.AWAITING_CONFIRMATION:
        allowed = {"confirmation"}
    else:
        allowed = {"full_name", "phone", "reason_for_visit", "preferred_slot_or_date", "confirmation"}

    if extraction.full_name and "full_name" in allowed:
        updates["full_name"] = extraction.full_name
    if extraction.phone and "phone" in allowed:
        # Normalize phone to digits-only for consistency
        digits_only = re.sub(r"\D", "", extraction.phone)
        updates["phone"] = digits_only if digits_only else extraction.phone
    if extraction.reason_for_visit and "reason_for_visit" in allowed:
        updates["reason_for_visit"] = extraction.reason_for_visit
    if extraction.preferred_slot_or_date and "preferred_slot_or_date" in allowed:
        slot = extraction.preferred_slot_or_date
        # If the slot is already an exact offered slot, use it directly to avoid
        # re-parsing the date year as a time in normalize_natural_slot.
        all_offered = store.get_offered_slots(session)
        if all_offered and any(slot == s for s in all_offered):
            updates["preferred_slot_or_date"] = slot
        else:
            # Slot may be a natural-language time/date; attempt normalization
            normalized = normalize_natural_slot(slot) or match_slot(slot, avail_svc.get_available_slots()) or slot
            updates["preferred_slot_or_date"] = normalized
    if extraction.doctor_name:
        updates["doctor_name"] = extraction.doctor_name
    if extraction.insurance_provider:
        updates["insurance_provider"] = extraction.insurance_provider
    if extraction.symptoms:
        existing = store.get_collected_data(session).get("symptoms", [])
        updates["symptoms"] = list(set(existing + extraction.symptoms))
    if extraction.notes:
        updates["notes"] = extraction.notes
    # Confirmation is only allowed in AWAITING_CONFIRMATION state
    if extraction.confirmation is not None and state == BookingState.AWAITING_CONFIRMATION:
        updates["confirmation"] = extraction.confirmation
    if extraction.reason_for_cancellation:
        updates["reason_for_cancellation"] = extraction.reason_for_cancellation
    if extraction.intent:
        session.intent = extraction.intent
    if updates:
        store.update_collected_data(session, updates)


def _run_triage(session: CallSession, message: str, extraction: ExtractionResult):
    combined = message
    if extraction.symptoms:
        combined += " " + " ".join(extraction.symptoms)
    if extraction.urgency_signals:
        combined += " " + " ".join(extraction.urgency_signals)
    if extraction.reason_for_visit:
        combined += " " + extraction.reason_for_visit

    urgency, signals = triage_svc.evaluate_urgency(combined)
    if urgency == UrgencyLevel.HIGH:
        session.urgency_level = "high"
        store.update_collected_data(session, {"urgency_signals": signals})
    elif urgency == UrgencyLevel.MEDIUM and session.urgency_level == "none":
        session.urgency_level = "medium"
    return urgency


def _detect_reschedule_intent(message: str, ai_result: Optional[ExtractionResult] = None) -> bool:
    if ai_result and ai_result.intent == "reschedule":
        return True
    msg = message.lower().strip()
    return any(kw in msg for kw in _RESCHEDULE_KEYWORDS)


_GREETING_WORDS = {"hi", "hello", "hey", "hiya", "howdy", "yo", "good morning", "good afternoon", "good evening"}


def _is_pure_greeting(message: str, ai_result: Optional[ExtractionResult] = None) -> bool:
    words = message.strip().lower().split()
    if not words:
        return False
    clean = " ".join(w.strip(",.!?") for w in words)
    if clean in _GREETING_WORDS:
        return True
    if clean.startswith("hi ") or clean.startswith("hello ") or clean.startswith("hey "):
        return True
    if len(words) <= 3 and ai_result and ai_result.intent == "general":
        return True
    return False


def _determine_next_state(session: CallSession, message: str = "", ai_result: Optional[ExtractionResult] = None) -> tuple:
    state = session.workflow_state or BookingState.GREETING
    collected = store.get_collected_data(session)

    if state == BookingState.GREETING:
        if collected.get("full_name"):
            return BookingState.AWAITING_PHONE, ""
        greeting_count = collected.get("greeting_count", 0)
        if _is_pure_greeting(message, ai_result) and greeting_count < 2:
            store.update_collected_data(session, {"greeting_count": greeting_count + 1})
            return BookingState.GREETING, ""
        return BookingState.AWAITING_NAME, ""

    if state == BookingState.AWAITING_NAME:
        if _is_in_correction_flow(session):
            return BookingState.AWAITING_NAME, "Could you please tell me your correct full name?"
        if collected.get("full_name"):
            return BookingState.AWAITING_PHONE, ""
        return BookingState.AWAITING_NAME, "I didn't quite catch your name. Could you please tell me your full name?"

    if state == BookingState.AWAITING_PHONE:
        if _is_in_correction_flow(session):
            return BookingState.AWAITING_PHONE, "Could you please provide your correct phone number?"
        if collected.get("phone"):
            return BookingState.AWAITING_REASON, ""
        return BookingState.AWAITING_PHONE, "What's the best phone number to reach you?"

    if state == BookingState.AWAITING_REASON:
        if _is_in_correction_flow(session):
            return BookingState.AWAITING_REASON, "What is the correct reason for your visit?"
        if collected.get("reason_for_visit"):
            return BookingState.AWAITING_SLOT_SELECTION, ""
        return BookingState.AWAITING_REASON, "What's the reason for your visit today?"

    if state == BookingState.AWAITING_SLOT_SELECTION:
        if _is_in_correction_flow(session):
            return BookingState.AWAITING_SLOT_SELECTION, "Could you select the correct available slot?"
        offered = store.get_offered_slots(session)
        selected = collected.get("preferred_slot_or_date")

        if not offered:
            slots = avail_svc.get_available_slots()
            store.update_offered_slots(session, slots)
            offered = slots

        if selected and any(selected == s for s in offered):
            session.selected_slot = selected
            return BookingState.AWAITING_CONFIRMATION, ""

        slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(offered[:7]))
        return BookingState.AWAITING_SLOT_SELECTION, (
            f"Here are the available slots for this week:\n{slot_list}\n\nWhich one works best for you?"
        )

    if state == BookingState.AWAITING_CONFIRMATION:
        confirmation = collected.get("confirmation")
        if confirmation is True:
            return BookingState.COMPLETED, ""
        if confirmation is False:
            store.update_collected_data(session, {"confirmation": None})
            return BookingState.AWAITING_SLOT_SELECTION, ""
        return BookingState.AWAITING_CONFIRMATION, ""

    return state, ""


def _generate_response(state: str, collected: dict, session: CallSession) -> str:
    name = collected.get("full_name", "")
    urgency = session.urgency_level
    greeting_count = collected.get("greeting_count", 0)

    if urgency == "high":
        return (
            "I understand. Based on what you've described, please seek urgent medical attention "
            "or call emergency services. I will escalate this to the clinic staff immediately."
        )

    greeting_messages = [
        "Hello, thank you for calling the clinic. How can I help you today?",
        "Hi there! How can I assist you with your appointment today?",
        "I'm here to help you get scheduled. Could you tell me your name and how I can help?",
    ]

    messages = {
        BookingState.GREETING: greeting_messages[min(greeting_count, len(greeting_messages) - 1)],
        BookingState.AWAITING_NAME: "I didn't quite catch your name. Could you please tell me your full name?",
        BookingState.AWAITING_PHONE: f"Thank you, {name}. What's the best phone number to reach you?",
        BookingState.AWAITING_REASON: "Thanks. What's the reason for your visit today?",
    }

    if state in messages:
        return messages[state]

    if state == BookingState.AWAITING_CONFIRMATION:
        slot = collected.get("preferred_slot_or_date", "")
        return (
            f"Great! Here's a summary of your booking:\n"
            f"- Name: {name}\n"
            f"- Phone: {collected.get('phone', '')}\n"
            f"- Reason: {collected.get('reason_for_visit', '')}\n"
            f"- Preferred Slot: {slot}\n\n"
            f"Shall I book this appointment for you?"
        )

    if state == BookingState.COMPLETED:
        slot = collected.get("preferred_slot_or_date", "")
        return (
            f"Perfect! Your appointment has been booked for {slot}. "
            f"We'll send a reminder before your visit. Is there anything else I can help with?"
        )

    return ""


def _build_workflow_context(session: CallSession, state: str, fallback_msg: str, last_user_message: str = "") -> dict:
    collected = store.get_collected_data(session)
    missing = _get_missing_fields(state, collected)
    return {
        "goal": _get_goal(state),
        "state": state,
        "known_fields": collected,
        "missing_fields": missing,
        "urgency_level": session.urgency_level,
        "assistant_goal": _get_goal(state),
        "fallback_template": fallback_msg,
        "last_user_message": last_user_message,
        "active_workflow": session.session_type or "booking",
    }


def _get_missing_fields(state: str, collected: dict) -> list[str]:
    if state == BookingState.GREETING:
        return ["full_name"]
    if state == BookingState.AWAITING_NAME:
        return ["full_name"] if not collected.get("full_name") else []
    if state == BookingState.AWAITING_PHONE:
        return ["phone"] if not collected.get("phone") else []
    if state == BookingState.AWAITING_REASON:
        return ["reason_for_visit"] if not collected.get("reason_for_visit") else []
    if state == BookingState.AWAITING_SLOT_SELECTION:
        return ["preferred_slot_or_date"] if not collected.get("preferred_slot_or_date") else []
    if state == BookingState.AWAITING_CONFIRMATION:
        return ["confirmation"]
    return []


def _get_goal(state: str) -> str:
    goals = {
        BookingState.GREETING: "greet_and_ask_name",
        BookingState.AWAITING_NAME: "ask_for_name",
        BookingState.AWAITING_PHONE: "ask_for_phone",
        BookingState.AWAITING_REASON: "ask_for_reason",
        BookingState.AWAITING_SLOT_SELECTION: "show_slots_and_ask_selection",
        BookingState.AWAITING_CONFIRMATION: "ask_confirmation",
        BookingState.COMPLETED: "confirm_completion",
    }
    return goals.get(state, "continue_conversation")


# ─── Reschedule helpers ───────────────────────────────────────────────────


def _reschedule_goal(state: str) -> str:
    goals = {
        RescheduleState.AWAITING_IDENTIFIER: "ask_for_phone",
        RescheduleState.AWAITING_NEW_SLOT: "ask_for_new_slot",
        RescheduleState.AWAITING_CONFIRMATION: "ask_confirmation",
        RescheduleState.COMPLETED: "confirm_completion",
    }
    return goals.get(state, "continue_conversation")


def _reschedule_generate_response(state: str, collected: dict, session: CallSession) -> str:
    if state == RescheduleState.AWAITING_IDENTIFIER:
        return "I'd be happy to help you reschedule. Could you please provide the phone number linked to your appointment?"
    if state == RescheduleState.AWAITING_NEW_SLOT:
        offered = store.get_offered_slots(session)
        slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(offered[:7]))
        return f"Here are the available slots:\n{slot_list}\n\nWhich one works best for you?"
    if state == RescheduleState.AWAITING_CONFIRMATION:
        old_slot = collected.get("current_slot", "")
        new_slot = collected.get("preferred_slot_or_date", "")
        return (
            f"Here's a summary of the change:\n"
            f"- Current slot: {old_slot}\n"
            f"- New slot: {new_slot}\n\n"
            f"Shall I go ahead and reschedule?"
        )
    if state == RescheduleState.COMPLETED:
        new_slot = collected.get("preferred_slot_or_date", "")
        return (
            f"Your appointment has been rescheduled to {new_slot}. "
            f"We'll send a reminder before your visit. Is there anything else I can help with?"
        )
    return ""


def _reschedule_deterministic_extraction(message: str, session: CallSession) -> ExtractionResult:
    result = ExtractionResult()
    state = session.workflow_state or ""
    collected = store.get_collected_data(session)

    if state == RescheduleState.AWAITING_IDENTIFIER:
        if not collected.get("phone"):
            phone = text_helpers.extract_phone(message)
            if phone:
                result.phone = phone
        if not collected.get("full_name"):
            name = text_helpers.extract_name(message)
            if not name:
                name = text_helpers.extract_name_simple(message)
            if name:
                result.full_name = name

    if state == RescheduleState.AWAITING_NEW_SLOT:
        offered = store.get_offered_slots(session)
        if offered:
            slot = match_slot(message, offered)
            if slot:
                result.preferred_slot_or_date = slot
            else:
                normalized = normalize_natural_slot(message)
                if normalized:
                    result.preferred_slot_or_date = normalized

    if state == RescheduleState.AWAITING_CONFIRMATION:
        if text_helpers.is_affirmative(message):
            result.confirmation = True
        elif text_helpers.is_negative(message):
            result.confirmation = False

    return result


def _safe_merge_reschedule_extraction(session: CallSession, extraction: ExtractionResult, state: str = None):
    """State-gated merge: only merge fields relevant to the current reschedule workflow state."""
    if state is None:
        state = session.workflow_state or RescheduleState.AWAITING_IDENTIFIER

    updates = {}

    if state == RescheduleState.AWAITING_IDENTIFIER:
        allowed = {"full_name", "phone"}
    elif state == RescheduleState.AWAITING_NEW_SLOT:
        allowed = {"preferred_slot_or_date"}
    elif state == RescheduleState.AWAITING_CONFIRMATION:
        allowed = {"confirmation"}
    else:
        allowed = set()

    if extraction.full_name and "full_name" in allowed:
        updates["full_name"] = extraction.full_name
    if extraction.phone and "phone" in allowed:
        digits_only = re.sub(r"\D", "", extraction.phone)
        updates["phone"] = digits_only if digits_only else extraction.phone
    if extraction.preferred_slot_or_date and "preferred_slot_or_date" in allowed:
        slot = extraction.preferred_slot_or_date
        normalized = normalize_natural_slot(slot) or match_slot(slot, avail_svc.get_available_slots()) or slot
        updates["preferred_slot_or_date"] = normalized
    if extraction.confirmation is not None and state == RescheduleState.AWAITING_CONFIRMATION:
        updates["confirmation"] = extraction.confirmation
    if extraction.notes:
        updates["notes"] = extraction.notes
    if updates:
        store.update_collected_data(session, updates)


def handle_reschedule_message(db: DBSession, session: CallSession, message: str) -> SendMessageResponse:
    store.append_transcript(session, "user", message)

    # 0. Check for smalltalk / side questions first
    smalltalk_response = _handle_smalltalk_and_queries(message, session, db)
    if smalltalk_response:
        store.append_transcript(session, "assistant", smalltalk_response)
        store.save_session(db, session)
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=smalltalk_response,
            workflow_state=session.workflow_state or RescheduleState.AWAITING_IDENTIFIER,
            collected_data=store.get_collected_data(session),
            intent=session.intent,
            urgency_level=session.urgency_level,
            completed=False,
        )

    # 1. Check for correction/confirmation flow first
    correction_result = _check_correction_flow(message, session)
    if correction_result is not None:
        ai_result = None
        fallback_result = correction_result
    else:
        # Normal extraction
        ai_result = _extract_from_ai(message, session)
        fallback_result = _reschedule_deterministic_extraction(message, session)

    state = session.workflow_state or RescheduleState.AWAITING_IDENTIFIER
    if ai_result:
        _safe_merge_reschedule_extraction(session, ai_result, state)
        if not ai_result.phone and fallback_result.phone:
            _safe_merge_reschedule_extraction(session, fallback_result, state)
        if not ai_result.full_name and fallback_result.full_name:
            _safe_merge_reschedule_extraction(session, fallback_result, state)
        if not ai_result.preferred_slot_or_date and fallback_result.preferred_slot_or_date:
            _safe_merge_reschedule_extraction(session, fallback_result, state)
        if ai_result.confirmation is None and fallback_result.confirmation is not None:
            _safe_merge_reschedule_extraction(session, fallback_result, state)
        if ai_result.confirmation is False and fallback_result.confirmation is True:
            _safe_merge_reschedule_extraction(session, fallback_result, state)
    else:
        _safe_merge_reschedule_extraction(session, fallback_result, state)

    collected = store.get_collected_data(session)
    new_state = state
    fallback_msg = ""
    completed = False
    appointment_id = None

    if state == RescheduleState.AWAITING_IDENTIFIER:
        phone = collected.get("phone")
        full_name = collected.get("full_name")
        if phone:
            appointment = apt_svc.find_upcoming_by_phone(db, phone)
            if appointment:
                patient = appointment.patient
                current_slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
                store.update_collected_data(session, {
                    "target_appointment_id": appointment.id,
                    "current_slot": current_slot,
                    "full_name": patient.full_name if patient else full_name or "Patient",
                    "phone": phone,
                })
                slots = avail_svc.get_available_slots()
                store.update_offered_slots(session, slots)
                slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots[:7]))
                new_state = RescheduleState.AWAITING_NEW_SLOT
                fallback_msg = (
                    f"I found your appointment on {current_slot}. "
                    f"Here are the available slots to switch to:\n{slot_list}\n\n"
                    f"Which one works best for you?"
                )
            else:
                fallback_msg = "I couldn't find any upcoming appointments linked to that number. Could you double-check the phone number?"
                new_state = RescheduleState.AWAITING_IDENTIFIER
        else:
            new_state = RescheduleState.AWAITING_IDENTIFIER

    elif state == RescheduleState.AWAITING_NEW_SLOT:
        selected = collected.get("preferred_slot_or_date")
        offered = store.get_offered_slots(session)
        if selected and any(selected == s for s in offered):
            store.update_collected_data(session, {"preferred_slot_or_date": selected})
            session.selected_slot = selected
            new_state = RescheduleState.AWAITING_CONFIRMATION
        elif not store.get_offered_slots(session):
            slots = avail_svc.get_available_slots()
            store.update_offered_slots(session, slots)
            slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots[:7]))
            new_state = RescheduleState.AWAITING_NEW_SLOT
            fallback_msg = (
                f"Here are the available slots:\n{slot_list}\n\n"
                f"Which one works best for you?"
            )
        else:
            slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(offered[:7]))
            new_state = RescheduleState.AWAITING_NEW_SLOT
            fallback_msg = (
                f"I didn't recognize that time. Here are the available slots:\n{slot_list}\n\n"
                f"Please pick one from the list."
            )

    elif state == RescheduleState.AWAITING_CONFIRMATION:
        if collected.get("confirmation") is True:
            target_id = collected.get("target_appointment_id")
            new_slot = collected.get("preferred_slot_or_date", "")
            date_str = new_slot.split(" at ")[0].split(" ")[-1] if " at " in new_slot else "Unknown"
            time_str = new_slot.split(" at ")[-1] if " at " in new_slot else "Unknown"
            result = apt_svc.reschedule_appointment(db, target_id, date_str, time_str)
            if result:
                old_slot = result["old_slot"]
                appointment = result["appointment"]
                appointment_id = appointment.id
                session.status = "completed"
                session.summary_text = summary_svc.generate_summary(db, session)
                evt_svc.log_event(db, session.id, EventType.APPOINTMENT_RESCHEDULED, {
                    "appointment_id": appointment_id,
                    "old_slot": old_slot,
                    "new_slot": new_slot,
                    "phone": collected.get("phone"),
                })
                evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
                new_state = RescheduleState.COMPLETED
                completed = True
        elif collected.get("confirmation") is False:
            slots = avail_svc.get_available_slots()
            store.update_offered_slots(session, slots)
            store.update_collected_data(session, {"confirmation": None, "preferred_slot_or_date": None})
            slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots[:7]))
            new_state = RescheduleState.AWAITING_NEW_SLOT
            fallback_msg = (
                f"No problem! Here are the available slots again:\n{slot_list}\n\n"
                f"Which one works best for you?"
            )
        else:
            new_state = RescheduleState.AWAITING_CONFIRMATION

    session.workflow_state = new_state
    store.update_collected_data(session, {"workflow_state": new_state})

    if completed:
        collected = store.get_collected_data(session)
        msg = _reschedule_generate_response(new_state, collected, session)
        store.append_transcript(session, "assistant", msg)
        store.save_session(db, session)
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=msg,
            workflow_state=new_state,
            collected_data=collected,
            intent=session.intent or "reschedule",
            urgency_level=session.urgency_level,
            appointment_id=appointment_id,
            completed=True,
        )

    fallback_response = _reschedule_generate_response(new_state, collected, session)
    if fallback_msg:
        fallback_response = fallback_msg

    collected_overrides = {k: v for k, v in collected.items()
                           if k in ("full_name", "phone", "current_slot", "preferred_slot_or_date", "target_appointment_id")}
    wc = {
        "goal": _reschedule_goal(new_state),
        "state": new_state,
        "known_fields": collected_overrides,
        "missing_fields": [],
        "urgency_level": session.urgency_level,
        "assistant_goal": _reschedule_goal(new_state),
        "fallback_template": fallback_response,
        "last_user_message": message,
        "active_workflow": "reschedule",
    }
    ai_response = ai_assistant_service.generate_response(wc)
    assistant_message = ai_response if ai_response else fallback_response

    store.append_transcript(session, "assistant", assistant_message)
    store.save_session(db, session)

    return SendMessageResponse(
        session_id=session.id,
        assistant_message=assistant_message,
        workflow_state=new_state,
        collected_data=store.get_collected_data(session),
        intent="reschedule",
        urgency_level=session.urgency_level,
        completed=False,
    )


def handle_cancel_message(db: DBSession, session: CallSession, message: str) -> SendMessageResponse:
    store.append_transcript(session, "user", message)

    # 0. Check for smalltalk / side questions first
    smalltalk_response = _handle_smalltalk_and_queries(message, session, db)
    if smalltalk_response:
        store.append_transcript(session, "assistant", smalltalk_response)
        store.save_session(db, session)
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=smalltalk_response,
            workflow_state=session.workflow_state or CancelState.AWAITING_IDENTIFIER,
            collected_data=store.get_collected_data(session),
            intent=session.intent,
            urgency_level=session.urgency_level,
            completed=False,
        )

    # 1. Check for correction flow first
    correction_result = _check_correction_flow(message, session)
    if correction_result is not None:
        ai_result = None
        fallback_result = correction_result
    else:
        # Normal extraction
        ai_result = _extract_from_ai(message, session)
        fallback_result = _cancel_deterministic_extraction(message, session)

    state = session.workflow_state or CancelState.AWAITING_IDENTIFIER

    if ai_result:
        _safe_merge_cancel_extraction(session, ai_result, state)
        if not ai_result.phone and fallback_result.phone:
            _safe_merge_cancel_extraction(session, fallback_result, state)
        if not ai_result.full_name and fallback_result.full_name:
            _safe_merge_cancel_extraction(session, fallback_result, state)
        if state == CancelState.AWAITING_CONFIRMATION and fallback_result.confirmation is not None:
            _safe_merge_cancel_extraction(session, fallback_result, state)
        elif ai_result.confirmation is None and fallback_result.confirmation is not None:
            _safe_merge_cancel_extraction(session, fallback_result, state)
    else:
        _safe_merge_cancel_extraction(session, fallback_result, state)

    collected = store.get_collected_data(session)
    new_state = state
    fallback_msg = ""
    completed = False
    appointment_id = None

    if state == CancelState.AWAITING_IDENTIFIER:
        phone = collected.get("phone")
        if phone:
            appointment = apt_svc.find_upcoming_by_phone(db, phone)
            if appointment:
                patient = appointment.patient
                current_slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
                store.update_collected_data(session, {
                    "target_appointment_id": appointment.id,
                    "current_slot": current_slot,
                    "full_name": patient.full_name if patient else collected.get("full_name", "Patient"),
                    "phone": phone,
                })
                new_state = CancelState.AWAITING_CONFIRMATION
                fallback_msg = (
                    f"I found your appointment on {current_slot}. "
                    "Are you sure you want to cancel this appointment?"
                )
            else:
                fallback_msg = (
                    "I couldn't find any upcoming appointments linked to that number. "
                    "Could you double-check the phone number?"
                )
                new_state = CancelState.AWAITING_IDENTIFIER
        else:
            new_state = CancelState.AWAITING_IDENTIFIER

    elif state == CancelState.AWAITING_CONFIRMATION:
        if collected.get("confirmation") is True:
            target_id = collected.get("target_appointment_id")
            result = apt_svc.cancel_appointment(db, target_id)
            if result:
                appointment_id = result.id
                session.status = "completed"
                session.summary_text = summary_svc.generate_summary(db, session)
                evt_svc.log_event(db, session.id, EventType.APPOINTMENT_CANCELLED, {
                    "appointment_id": appointment_id,
                    "phone": collected.get("phone"),
                })
                evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
                new_state = CancelState.COMPLETED
                completed = True
        elif collected.get("confirmation") is False:
            new_state = CancelState.COMPLETED
            session.status = "completed"
            store.update_collected_data(session, {"cancel_declined": True})
            session.summary_text = summary_svc.generate_summary(db, session)
            evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
            completed = True
        else:
            new_state = CancelState.AWAITING_CONFIRMATION
            fallback_msg = "To continue, please confirm whether you want to cancel your appointment."

    session.workflow_state = new_state
    store.update_collected_data(session, {"workflow_state": new_state})

    if completed:
        collected = store.get_collected_data(session)
        msg = _cancel_generate_response(new_state, collected, session)
        store.append_transcript(session, "assistant", msg)
        store.save_session(db, session)
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=msg,
            workflow_state=new_state,
            collected_data=collected,
            intent=session.intent or "cancel",
            urgency_level=session.urgency_level,
            appointment_id=appointment_id,
            completed=True,
        )

    fallback_response = _cancel_generate_response(new_state, collected, session)
    if fallback_msg:
        fallback_response = fallback_msg

    collected_overrides = {k: v for k, v in collected.items()
                           if k in ("full_name", "phone", "current_slot", "target_appointment_id")}
    wc = {
        "goal": _cancel_goal(new_state),
        "state": new_state,
        "known_fields": collected_overrides,
        "missing_fields": [],
        "urgency_level": session.urgency_level,
        "assistant_goal": _cancel_goal(new_state),
        "fallback_template": fallback_response,
        "last_user_message": message,
        "active_workflow": "cancel",
    }
    ai_response = ai_assistant_service.generate_response(wc)
    assistant_message = ai_response if ai_response else fallback_response

    store.append_transcript(session, "assistant", assistant_message)
    store.save_session(db, session)

    return SendMessageResponse(
        session_id=session.id,
        assistant_message=assistant_message,
        workflow_state=new_state,
        collected_data=store.get_collected_data(session),
        intent="cancel",
        urgency_level=session.urgency_level,
        completed=False,
    )


def _cancel_goal(state: str) -> str:
    goals = {
        CancelState.AWAITING_IDENTIFIER: "ask_for_phone",
        CancelState.AWAITING_CONFIRMATION: "ask_confirmation",
        CancelState.COMPLETED: "confirm_completion",
    }
    return goals.get(state, "continue_conversation")


def _cancel_generate_response(state: str, collected: dict, session: CallSession) -> str:
    if state == CancelState.AWAITING_IDENTIFIER:
        return "I'd be happy to help you cancel your appointment. Could you please provide the phone number linked to your appointment?"
    if state == CancelState.AWAITING_CONFIRMATION:
        current_slot = collected.get("current_slot", "")
        return (
            f"I found your appointment on {current_slot}. "
            "Are you sure you want to cancel this appointment?"
        )
    if state == CancelState.COMPLETED:
        if collected.get("cancel_declined") is True or collected.get("target_appointment_id") is None:
            return "No problem. Your appointment remains scheduled. Is there anything else I can help with?"
        return "Your appointment has been cancelled. Is there anything else I can help with?"
    return ""


def _cancel_deterministic_extraction(message: str, session: CallSession) -> ExtractionResult:
    result = ExtractionResult()
    state = session.workflow_state or ""
    collected = store.get_collected_data(session)

    if state == CancelState.AWAITING_IDENTIFIER:
        phone = text_helpers.extract_phone(message)
        if phone:
            result.phone = phone
        if not collected.get("full_name"):
            name = text_helpers.extract_name(message)
            if not name:
                name = text_helpers.extract_name_simple(message)
            if name:
                result.full_name = name

    if state == CancelState.AWAITING_CONFIRMATION:
        if text_helpers.is_affirmative(message):
            result.confirmation = True
        elif text_helpers.is_negative(message):
            result.confirmation = False

    return result


def _safe_merge_cancel_extraction(session: CallSession, extraction: ExtractionResult, state: str = None):
    """State-gated merge for cancel: only merge fields relevant to the current cancel workflow state."""
    if state is None:
        state = session.workflow_state or CancelState.AWAITING_IDENTIFIER

    updates = {}

    if state == CancelState.AWAITING_IDENTIFIER:
        allowed = {"full_name", "phone"}
    elif state == CancelState.AWAITING_CONFIRMATION:
        allowed = {"confirmation"}
    else:
        allowed = set()

    if extraction.full_name and "full_name" in allowed:
        updates["full_name"] = extraction.full_name
    if extraction.phone and "phone" in allowed:
        digits_only = re.sub(r"\D", "", extraction.phone)
        updates["phone"] = digits_only if digits_only else extraction.phone
    if extraction.confirmation is not None and "confirmation" in allowed:
        updates["confirmation"] = extraction.confirmation
    if extraction.notes:
        updates["notes"] = extraction.notes
    if updates:
        store.update_collected_data(session, updates)


# ─── Booking flow ─────────────────────────────────────────────────────────


def _try_handle_correction(message: str, session: CallSession) -> tuple[bool, str]:
    """Detect and handle correction phrases. Returns (handled, response_or_empty)."""
    lower = message.lower().strip()

    # Check for explicit correction patterns
    patterns = {
        "full_name": [
            "that's not my name", "not my name", "wrong name", "incorrect name",
            "my name is not", "you got my name wrong", "that's not me", "not me",
        ],
        "phone": [
            "that's not my number", "not my number", "wrong number", "incorrect number",
            "my number is not", "you got my number wrong", "wrong phone",
        ],
        "reason_for_visit": [
            "that's not right", "not for that", "wrong reason", "not the reason",
            "i didn't say that", "that's not what i said",
        ],
        "preferred_slot_or_date": [
            "that's not the right time", "wrong time", "wrong slot", "not that slot",
            "i meant", "not that date", "different time", "different slot",
        ],
    }

    for field, pats in patterns.items():
        for pat in pats:
            if pat in lower:
                mem.set_correction_target(session, field)
                mem.dispute_field(session, field)
                mem.clear_field(session, field)
                return True, field

    # Natural re-statement corrections: "actually my name is..."
    natural_corrections = {
        "full_name": [r"(?:actually|no,)\s+(?:my name is|my correct name is|i'm)"],
        "phone": [r"(?:actually|no,)\s+(?:my number is|my phone is)"],
        "reason_for_visit": [r"(?:actually|no,)\s+(?:i need to|the reason is)"],
    }
    for field, pats in natural_corrections.items():
        for pat in pats:
            if re.search(pat, lower):
                mem.set_correction_target(session, field)
                mem.dispute_field(session, field)
                mem.clear_field(session, field)
                return True, field

    return False, ""


def handle_booking_message(db: DBSession, session: CallSession, message: str) -> SendMessageResponse:
    store.append_transcript(session, "user", message)

    # 0. Check for correction/confirmation flow first (BEFORE smalltalk/extraction)
    correction_handled, correction_field = _try_handle_correction(message, session)
    if correction_handled:
        # If user is correcting, enter correction flow and respond immediately
        state_map = {
            "full_name": (BookingState.AWAITING_NAME, "I apologize for the confusion. Could you please tell me your correct full name?"),
            "phone": (BookingState.AWAITING_PHONE, "I apologize for the confusion. Could you please provide your correct phone number?"),
            "reason_for_visit": (BookingState.AWAITING_REASON, "I apologize for the confusion. What is the correct reason for your visit?"),
            "preferred_slot_or_date": (BookingState.AWAITING_SLOT_SELECTION, "I apologize for the confusion. Could you select the correct available slot?"),
        }
        new_state, fallback_msg = state_map.get(correction_field, (session.workflow_state or BookingState.GREETING, ""))
        session.workflow_state = new_state
        store.update_collected_data(session, {"workflow_state": new_state})
        store.append_transcript(session, "assistant", fallback_msg)
        store.save_session(db, session)
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=fallback_msg,
            workflow_state=new_state,
            collected_data=store.get_collected_data(session),
            intent=session.intent,
            urgency_level=session.urgency_level,
            completed=False,
        )

    correction_result = _check_correction_flow(message, session)
    if correction_result is not None:
        ai_result = None
        fallback_result = correction_result
    else:
        # Normal flow: check for smalltalk / queries first
        smalltalk_response = _handle_smalltalk_and_queries(message, session, db)
        if smalltalk_response:
            store.append_transcript(session, "assistant", smalltalk_response)
            store.save_session(db, session)
            return SendMessageResponse(
                session_id=session.id,
                assistant_message=smalltalk_response,
                workflow_state=session.workflow_state or BookingState.GREETING,
                collected_data=store.get_collected_data(session),
                intent=session.intent,
                urgency_level=session.urgency_level,
                completed=False,
            )

        # Normal extraction
        ai_result = _extract_from_ai(message, session)
        fallback_result = _deterministic_extraction(message, session)

    state = session.workflow_state or BookingState.GREETING
    if ai_result:
        _safe_merge_extraction(session, ai_result, state)
        if not ai_result.full_name and fallback_result.full_name:
            _safe_merge_extraction(session, fallback_result, state)
        elif not ai_result.phone and fallback_result.phone:
            _safe_merge_extraction(session, fallback_result, state)
        elif not ai_result.reason_for_visit and fallback_result.reason_for_visit:
            _safe_merge_extraction(session, fallback_result, state)
        elif not ai_result.preferred_slot_or_date and fallback_result.preferred_slot_or_date:
            _safe_merge_extraction(session, fallback_result, state)
        if ai_result.confirmation is None and fallback_result.confirmation is not None:
            _safe_merge_extraction(session, fallback_result, state)
        if ai_result.confirmation is False and fallback_result.confirmation is True:
            _safe_merge_extraction(session, fallback_result, state)

        triage_result = _run_triage(session, message, ai_result)
    else:
        _safe_merge_extraction(session, fallback_result, state)
        triage_result = _run_triage(session, message, fallback_result)

    extracted = ai_result if ai_result else fallback_result
    if extracted:
        evt_svc.log_event(
            db, session.id, EventType.FIELD_COLLECTED,
            {"fields": {k: v for k, v in extracted.model_dump().items() if v}},
        )

    new_state, fallback_msg = _determine_next_state(session, message, ai_result)
    session.workflow_state = new_state
    store.update_collected_data(session, {"workflow_state": new_state})

    if new_state == BookingState.AWAITING_SLOT_SELECTION and not store.get_offered_slots(session):
        slots = avail_svc.get_available_slots()
        store.update_offered_slots(session, slots)
        slot_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots[:7]))
        fallback_msg = (
            f"Here are the available slots for this week:\n{slot_list}\n\n"
            f"Which one works best for you?"
        )

    if new_state == BookingState.COMPLETED:
        collected = store.get_collected_data(session)
        full_name = collected.get("full_name", "Unknown")
        phone = collected.get("phone", "000-000-0000")
        
        # Duplicate-booking protection: check if an upcoming appointment exists
        existing_appointment = apt_svc.find_existing_appointment_by_name_phone(db, full_name, phone)
        if existing_appointment:
            session.status = "completed"
            session.summary_text = summary_svc.generate_summary(db, session)
            slot_str = f"{existing_appointment.scheduled_date} at {existing_appointment.scheduled_time}"
            msg = (
                f"I see you already have an upcoming appointment on {slot_str}. "
                "You cannot book another one with the same details. "
                "Let me know if you need to reschedule or cancel that appointment."
            )
            store.append_transcript(session, "assistant", msg)
            store.save_session(db, session)
            evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
            return SendMessageResponse(
                session_id=session.id,
                assistant_message=msg,
                workflow_state=new_state,
                collected_data=store.get_collected_data(session),
                intent=session.intent,
                urgency_level=session.urgency_level,
                appointment_id=existing_appointment.id,
                completed=True,
            )

        patient = apt_svc.find_or_create_patient(
            db,
            full_name=full_name,
            phone=phone,
            insurance_provider=collected.get("insurance_provider"),
        )
        session.patient_id = patient.id

        slot = session.selected_slot or collected.get("preferred_slot_or_date", "")
        date_str = slot.split(" at ")[0].split(" ")[-1] if " at " in slot else "Unknown"
        time_str = slot.split(" at ")[-1] if " at " in slot else "Unknown"

        appointment = apt_svc.create_appointment(
            db,
            patient_id=patient.id,
            scheduled_date=date_str,
            scheduled_time=time_str,
            reason_for_visit=collected.get("reason_for_visit", "Not specified"),
            doctor_name=collected.get("doctor_name"),
            notes=collected.get("notes"),
        )
        session.status = "completed"
        session.summary_text = summary_svc.generate_summary(db, session)

        evt_svc.log_event(db, session.id, EventType.APPOINTMENT_CREATED, {
            "appointment_id": appointment.id,
            "patient_id": patient.id,
            "slot": slot,
        })
        evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
        store.save_session(db, session)

        store.append_transcript(session, "assistant", _generate_response(new_state, collected, session))
        store.save_session(db, session)

        return SendMessageResponse(
            session_id=session.id,
            assistant_message=_generate_response(new_state, collected, session),
            workflow_state=new_state,
            collected_data=store.get_collected_data(session),
            intent=session.intent,
            urgency_level=session.urgency_level,
            appointment_id=appointment.id,
            completed=True,
        )

    if triage_result == UrgencyLevel.HIGH:
        evt_svc.log_event(db, session.id, EventType.ESCALATION_TRIGGERED, {
            "urgency": "high",
            "signals": store.get_collected_data(session).get("urgency_signals", []),
        })

    workflow_context = _build_workflow_context(session, new_state, fallback_msg, message)
    ai_response = ai_assistant_service.generate_response(workflow_context)
    if ai_response:
        assistant_message = ai_response
    else:
        assistant_message = _generate_response(new_state, store.get_collected_data(session), session) or fallback_msg or "I'm ready to help. Could you tell me what you need?"

    store.append_transcript(session, "assistant", assistant_message)
    store.save_session(db, session)

    return SendMessageResponse(
        session_id=session.id,
        assistant_message=assistant_message,
        workflow_state=new_state,
        collected_data=store.get_collected_data(session),
        intent=session.intent,
        urgency_level=session.urgency_level,
        completed=False,
    )


def _detect_unified_intent(message: str) -> str:
    """Lightweight intent detection for unified entrypoint."""
    lower = message.lower().strip()
    
    # Check for explicit cancel keywords first
    cancel_keywords = [
        "cancel", "cancelled", "cancel my", "cancel an", "cancel the",
        "cancel appointment", "cancel my appointment", "i want to cancel",
        "i'd like to cancel", "i would like to cancel",
    ]
    for kw in cancel_keywords:
        if kw in lower:
            return "cancel"
    
    # Check for reschedule keywords
    reschedule_keywords = [
        "reschedule", "move my appointment", "change my appointment",
        "shift my slot", "change appointment time", "move appointment",
        "shift appointment", "reschedule appointment", "change my booking",
        "move my booking", "i want to reschedule", "i'd like to reschedule",
    ]
    for kw in reschedule_keywords:
        if kw in lower:
            return "reschedule"
    
    # Check for booking keywords
    booking_keywords = [
        "book", "schedule", "make an appointment", "new appointment",
        "get an appointment", "see a doctor", "appointment for",
        "i want to book", "i'd like to book", "i want an appointment",
    ]
    for kw in booking_keywords:
        if kw in lower:
            return "booking"
    
    return "booking"  # Default to booking for general queries


def _route_to_cancel(session: CallSession) -> bool:
    ws = (session.workflow_state or "") if session.workflow_state else ""
    return ws.startswith("cancel_") or (session.session_type or "") == "cancel"


def _route_to_reschedule(session: CallSession) -> bool:
    ws = (session.workflow_state or "") if session.workflow_state else ""
    return ws.startswith("reschedule_") or (session.session_type or "") == "reschedule"


def handle_message(db: DBSession, session: CallSession, message: str) -> SendMessageResponse:
    from app.services.engine import ConversationEngine, detect_intent

    # Unified session: detect intent from first message and set session type
    # Return the appropriate greeting WITHOUT extracting data from the intent message
    # Only run this ONCE — on the very first message (workflow_state is None/greeting)
    ws = session.workflow_state or ""
    # Only run first-message intent detection if intent is NOT already set to a workflow
    if ((session.session_type or "") == "unified" and ws in ("", "greeting", None)
            and (not session.intent or session.intent == "unknown")):
        detected_intent = detect_intent(message)
        session.session_type = detected_intent if detected_intent in ("booking", "reschedule", "cancel") else "unified"
        session.intent = detected_intent if detected_intent in ("booking", "reschedule", "cancel") else "unknown"

        if detected_intent == "cancel":
            session.workflow_state = CancelState.AWAITING_IDENTIFIER
            greeting = "I'd be happy to help you cancel your appointment. Could you please provide the phone number linked to your appointment?"
        elif detected_intent == "reschedule":
            session.workflow_state = RescheduleState.AWAITING_IDENTIFIER
            greeting = "I'd be happy to help you reschedule your appointment. Could you please provide the phone number linked to your appointment?"
        elif detected_intent == "booking":
            session.session_type = "booking"
            session.workflow_state = BookingState.GREETING
            greeting = "Hello, thank you for calling the clinic. How can I help you today?"
        else:
            # Unknown/smalltalk — stay in unified, don't force booking
            session.workflow_state = "AWAITING_NAME"
            greeting = "Hello! I'm ClinicFlow's virtual receptionist. I can help you book, reschedule, or cancel an appointment. Could you please tell me your full name?"

        store.append_transcript(session, "user", message)
        store.append_transcript(session, "assistant", greeting)
        store.save_session(db, session)

        return SendMessageResponse(
            session_id=session.id,
            assistant_message=greeting,
            workflow_state=session.workflow_state,
            collected_data=store.get_collected_data(session),
            intent=session.intent,
            urgency_level=session.urgency_level,
            completed=False,
        )

    return ConversationEngine.process(db, session, message)


def handle_start_session(db: DBSession, session_type: str, channel: str = "simulated") -> tuple[CallSession, str]:
    session = store.create_session(db, session_type, channel)

    evt_svc.log_event(db, session.id, EventType.SESSION_STARTED, {
        "session_type": session_type,
        "channel": channel,
    })

    if session_type == "reschedule":
        session.workflow_state = RescheduleState.AWAITING_IDENTIFIER
        session.intent = "reschedule"
        greeting = "I'd be happy to help you reschedule your appointment. Could you please provide the phone number linked to your appointment?"
    elif session_type == "cancel":
        session.workflow_state = CancelState.AWAITING_IDENTIFIER
        session.intent = "cancel"
        greeting = "I'd be happy to help you cancel your appointment. Could you please provide the phone number linked to your appointment?"
    else:
        greeting = "Hello, thank you for calling the clinic. How can I help you today? You can book a new appointment, reschedule an existing one, or cancel an appointment."
    store.append_transcript(session, "assistant", greeting)
    store.save_session(db, session)

    return session, greeting
