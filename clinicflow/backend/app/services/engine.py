"""
Unified Conversation Engine for ClinicFlow.

Replaces the three separate booking/reschedule/cancel handlers with one
data-driven engine. Each workflow is defined as configuration (states,
allowed fields, transitions) and the engine processes messages through
a common pipeline.
"""

from datetime import date, datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.core.constants import BookingState, CancelState, EventType, RescheduleState
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
from app.utils.slot_utils import match_slot, normalize_natural_slot, format_slot_for_speech
import re


# ─── Workflow Configuration ─────────────────────────────────────────────
# This single data structure replaces 3 duplicated _safe_merge_* functions.

BOOKING_EXTRACT = {
    BookingState.GREETING: {"full_name"},
    BookingState.AWAITING_NAME: {"full_name"},
    BookingState.AWAITING_PHONE: {"phone"},
    BookingState.AWAITING_SLOT_SELECTION: {"preferred_slot_or_date"},
    BookingState.AWAITING_CONFIRMATION: {"confirmation"},
}

BOOKING_MERGE = {
    BookingState.GREETING: {"full_name", "preferred_slot_or_date"},
    BookingState.AWAITING_NAME: {"full_name", "preferred_slot_or_date"},
    BookingState.AWAITING_PHONE: {"phone"},
    BookingState.AWAITING_SLOT_SELECTION: {"preferred_slot_or_date"},
    BookingState.AWAITING_CONFIRMATION: {"confirmation"},
}

RESCHEDULE_MERGE = {
    RescheduleState.AWAITING_IDENTIFIER: {"full_name", "phone"},
    RescheduleState.AWAITING_APPOINTMENT_SELECTION: set(),
    RescheduleState.AWAITING_NEW_SLOT: {"preferred_slot_or_date"},
    RescheduleState.AWAITING_CONFIRMATION: {"confirmation"},
}

CANCEL_MERGE = {
    CancelState.AWAITING_IDENTIFIER: {"full_name", "phone"},
    CancelState.AWAITING_APPOINTMENT_SELECTION: set(),
    CancelState.AWAITING_CONFIRMATION: {"confirmation"},
}

# ─── Workflow Lock Helpers ───────────────────────────────────────────

def _get_active_intent(session):
    """Return the active intent from session or collected data, or 'unknown'."""
    intent = session.session_type
    if not intent and session.intent and session.intent != "unknown":
        intent = session.intent
    if not intent:
        collected = store.get_collected_data(session)
        intent = collected.get("session_intent", "")
    return intent if intent else "unknown"


def _is_explicit_workflow_change(message: str, current_intent: str) -> bool:
    """Detect if the user is explicitly requesting a workflow change."""
    lower = message.lower().strip()
    change_phrases = [
        "actually i want to book", "i want to book", "i'd like to book",
        "actually i want to schedule", "i want to schedule",
        "actually i want to reschedule", "i want to reschedule", "i'd like to reschedule",
        "actually i want to cancel", "i want to cancel", "i'd like to cancel",
        "book instead", "schedule instead", "reschedule instead", "cancel instead",
        "no, book", "no, schedule", "no, reschedule", "no, cancel",
        "change to booking", "change to reschedule", "change to cancel",
    ]
    return any(phrase in lower for phrase in change_phrases)


def _can_change_intent(session: CallSession, new_intent: str, message: str = "") -> bool:
    """
    Gate intent changes. Once a session has an active workflow intent,
    do NOT switch unless the user explicitly requests it.
    """
    current_intent = _get_active_intent(session)
    if not current_intent or current_intent == new_intent:
        return True
    # Prevent switching from an active workflow to another without explicit request
    if current_intent in ("booking", "reschedule", "cancel") and new_intent in ("booking", "reschedule", "cancel"):
        return _is_explicit_workflow_change(message, current_intent)
    return True


def record_intent(session: CallSession, intent: str, reason: str, message: str = "") -> bool:
    """Record the intent change if allowed. Returns True if accepted, False if blocked."""
    if intent in ("booking", "reschedule", "cancel"):
        if not _can_change_intent(session, intent, message):
            return False
        session.session_type = intent
        session.intent = intent
        store.update_collected_data(session, {"session_intent": intent})
    else:
        session.intent = intent
    return True

# Field ask-prompt per state
BOOKING_ASK = {
    BookingState.GREETING: "Could you please tell me your full name?",
    BookingState.AWAITING_NAME: "Could you please tell me your full name?",
    BookingState.AWAITING_PHONE: "What's the best phone number to reach you?",
    BookingState.AWAITING_REASON: "What's the reason for your visit today?",
    BookingState.AWAITING_SLOT_SELECTION: "Could you select an available slot?",
    BookingState.AWAITING_CONFIRMATION: "Shall I book this appointment for you?",
}

RESCHEDULE_ASK = {
    RescheduleState.AWAITING_IDENTIFIER: "Could you please provide the phone number linked to your appointment?",
    RescheduleState.AWAITING_NEW_SLOT: "Which slot works best for you?",
    RescheduleState.AWAITING_CONFIRMATION: "Shall I go ahead and reschedule?",
}

CANCEL_ASK = {
    CancelState.AWAITING_IDENTIFIER: "Could you please provide the phone number linked to your appointment?",
    CancelState.AWAITING_CONFIRMATION: "Are you sure you want to cancel this appointment?",
}

BOOKING_GOALS = {
    BookingState.GREETING: "greet_and_ask_name",
    BookingState.AWAITING_NAME: "ask_for_name",
    BookingState.AWAITING_PHONE: "ask_for_phone",
    BookingState.AWAITING_REASON: "ask_for_reason",
    BookingState.AWAITING_SLOT_SELECTION: "show_slots_and_ask_selection",
    BookingState.AWAITING_CONFIRMATION: "ask_confirmation",
    BookingState.COMPLETED: "confirm_completion",
}

RESCHEDULE_GOALS = {
    RescheduleState.AWAITING_IDENTIFIER: "ask_for_phone",
    RescheduleState.AWAITING_NEW_SLOT: "ask_for_new_slot",
    RescheduleState.AWAITING_CONFIRMATION: "ask_confirmation",
    RescheduleState.COMPLETED: "confirm_completion",
}

CANCEL_GOALS = {
    CancelState.AWAITING_IDENTIFIER: "ask_for_phone",
    CancelState.AWAITING_CONFIRMATION: "ask_confirmation",
    CancelState.COMPLETED: "confirm_completion",
}

_RESCHEDULE_KEYWORDS = [
    "reschedule", "move my appointment", "change my appointment",
    "shift my appointment", "change appointment time",
    "move appointment", "shift appointment", "reschedule appointment",
    "change my booking", "move my booking",
]

_CANCEL_KEYWORDS = [
    "cancel", "cancelled", "cancel my", "cancel an", "cancel the",
    "cancel appointment", "cancel my appointment", "i want to cancel",
    "i'd like to cancel", "i would like to cancel",
]

_BOOKING_KEYWORDS = [
    "book", "schedule", "make an appointment", "new appointment",
    "get an appointment", "see a doctor", "appointment for",
    "i want to book", "i'd like to book", "i want an appointment",
]

_GREETING_WORDS = {"hi", "hello", "hey", "hiya", "howdy", "yo", "good morning", "good afternoon", "good evening"}

_SKIP_WORDS = {
    "hi", "hello", "hey", "hiya", "howdy", "yo",
    "i", "my", "the", "a", "an", "to", "for", "in", "on", "at", "is", "am", "it", "me", "i'm",
    "ok", "okay", "yes", "yeah", "yep", "sure", "right", "correct",
    "no", "nope", "nah", "not", "don't", "dont",
    "book", "booking", "schedule", "scheduling", "appointment", "appointments",
    "cancel", "cancellation", "cancelled", "reschedule", "rescheduling",
    "help", "please", "thanks", "thank", "sorry",
}


# ─── Field-Answer Guard (delegates to text_helpers) ───────────────────────

def _is_plausible_name(text: str, state: str) -> bool:
    """Reject generic responses and intent statements as names."""
    return text_helpers.is_plausible_name(text)


def _is_plausible_phone(text: str) -> bool:
    """Only accept strings with enough digits to be a phone number."""
    return text_helpers.is_plausible_phone(text)


def _is_plausible_reason(text: str) -> bool:
    """Reason should be free text; reject pure yes/no."""
    return text_helpers.is_plausible_reason(text)


def _is_plausible_slot(text: str) -> bool:
    """Slot-ish strings contain date/time indicators or numeric selection."""
    return text_helpers.is_plausible_slot(text)


# ─── State Machine Helpers ──────────────────────────────────────────────────

def _next_booking_state(db: DBSession, session: CallSession, message: str = "", ai_result: Optional[ExtractionResult] = None) -> tuple[str, str]:
    """Determine next booking state. Returns (new_state, fallback_msg)."""
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
        if mem.get_correction_target(session):
            return BookingState.AWAITING_NAME, "Could you please tell me your correct full name?"
        if collected.get("full_name"):
            _reset_ask_tracking(session)
            return BookingState.AWAITING_PHONE, ""
        repeat = _track_ask(session, "full_name")
        if repeat >= 3:
            return BookingState.AWAITING_NAME, (
                "I really need your full name to proceed with the booking. "
                "Could you please type it in? For example: 'John Smith'."
            )
        if repeat >= 2:
            return BookingState.AWAITING_NAME, (
                "I didn't catch your name. Could you please tell me your full name?"
            )
        return BookingState.AWAITING_NAME, "I didn't quite catch your name. Could you please tell me your full name?"

    if state == BookingState.AWAITING_PHONE:
        if mem.get_correction_target(session):
            return BookingState.AWAITING_PHONE, "Could you please provide your correct phone number?"
        if collected.get("phone"):
            _reset_ask_tracking(session)
            if session.intent == "unknown":
                return BookingState.AWAITING_PHONE, ""
            return BookingState.AWAITING_SLOT_SELECTION, ""
        repeat = _track_ask(session, "phone")
        if repeat >= 3:
            return BookingState.AWAITING_PHONE, (
                "I need a phone number to continue. Please enter a 10-digit number like '555-123-4567'."
            )
        if repeat >= 2:
            return BookingState.AWAITING_PHONE, (
                "I still need your phone number. What's the best number to reach you?"
            )
        name = collected.get("full_name", "")
        return BookingState.AWAITING_PHONE, (
            f"Thank you, {name}. What's the best phone number to reach you?" if name
            else "What's the best phone number to reach you?"
        )

    if state == BookingState.AWAITING_SLOT_SELECTION:
        if mem.get_correction_target(session):
            return BookingState.AWAITING_SLOT_SELECTION, "Could you select the correct available slot?"
        offered = store.get_offered_slots(session)
        selected = collected.get("preferred_slot_or_date")

        if not offered:
            slots = avail_svc.get_available_slots(db)
            store.update_offered_slots(session, slots)
            offered = slots

        if selected and any(selected == s or s.startswith(selected) for s in offered):
            _reset_ask_tracking(session)
            session.selected_slot = selected
            return BookingState.AWAITING_CONFIRMATION, ""

        repeat = _track_ask(session, "preferred_slot_or_date")
        slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
        if repeat >= 3:
            return BookingState.AWAITING_SLOT_SELECTION, (
                f"Here are the available slots — please type the number of your choice:\n{slot_list}"
            )
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


# ─── Deterministic Extraction (fast, no LLM) ──────────────────────────────

def _deterministic_extract_booking(message: str, session: CallSession) -> ExtractionResult:
    result = ExtractionResult()
    state = session.workflow_state or BookingState.GREETING
    collected = store.get_collected_data(session)

    if state in (BookingState.GREETING, BookingState.AWAITING_NAME):
        if not collected.get("full_name"):
            # Only extract name from clean, short messages that look like names
            # Do NOT extract from long/combined messages — let AI handle those
            stripped = message.strip()
            if len(stripped) <= 40:
                name = text_helpers.extract_name(stripped)
                if name and _is_plausible_name(name, state) and name.lower() not in _SKIP_WORDS:
                    # Final check: name should be mostly alphabetic
                    alpha_ratio = sum(1 for c in name if c.isalpha() or c == ' ') / max(len(name), 1)
                    if alpha_ratio >= 0.8:
                        result.full_name = name

    if state == BookingState.AWAITING_PHONE:
        if not collected.get("phone"):
            phone = text_helpers.extract_phone(message)
            if phone:
                result.phone = phone

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
        else:
            # If nothing offered yet, require plausible slot-like input
            if _is_plausible_slot(message):
                normalized = normalize_natural_slot(message)
                if normalized:
                    result.preferred_slot_or_date = normalized

    if state == BookingState.AWAITING_CONFIRMATION:
        if text_helpers.is_affirmative(message):
            result.confirmation = True
        elif text_helpers.is_negative(message):
            result.confirmation = False

    return result


def _deterministic_extract_reschedule(message: str, session: CallSession) -> ExtractionResult:
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
                if name and (name.lower() in _SKIP_WORDS or not _is_plausible_name(name, state)):
                    name = None
            if name and _is_plausible_name(name, state):
                result.full_name = name

    if state == RescheduleState.AWAITING_APPOINTMENT_SELECTION:
        candidates = collected.get("_all_appointments", [])
        if candidates:
            user_lower = message.strip().lower()
            idx = None
            if user_lower.isdigit():
                i = int(user_lower) - 1
                if 0 <= i < len(candidates):
                    idx = i
            else:
                for i, c in enumerate(candidates):
                    if any(word in user_lower for word in c["slot"].lower().split()):
                        idx = i
                        break
            if idx is not None:
                store.update_collected_data(session, {
                    "target_appointment_id": candidates[idx]["id"],
                    "current_slot": candidates[idx]["slot"],
                    "full_name": candidates[idx]["patient_name"],
                    "_appointment_selected": True,
                })
                mem.set_field(session, "appointment_id", candidates[idx]["id"])
                mem.confirm_field(session, "appointment_id")

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


def _deterministic_extract_cancel(message: str, session: CallSession) -> ExtractionResult:
    result = ExtractionResult()
    state = session.workflow_state or ""
    collected = store.get_collected_data(session)

    if state == CancelState.AWAITING_IDENTIFIER:
        if not collected.get("phone"):
            phone = text_helpers.extract_phone(message)
            if phone:
                result.phone = phone
        if not collected.get("full_name"):
            name = text_helpers.extract_name(message)
            if not name:
                name = text_helpers.extract_name_simple(message)
                if name and (name.lower() in _SKIP_WORDS or not _is_plausible_name(name, state)):
                    name = None
            if name and _is_plausible_name(name, state):
                result.full_name = name

    if state == CancelState.AWAITING_APPOINTMENT_SELECTION:
        candidates = collected.get("_all_appointments", [])
        if candidates:
            user_lower = message.strip().lower()
            idx = None
            if user_lower.isdigit():
                i = int(user_lower) - 1
                if 0 <= i < len(candidates):
                    idx = i
            else:
                for i, c in enumerate(candidates):
                    if any(word in user_lower for word in c["slot"].lower().split()):
                        idx = i
                        break
            if idx is not None:
                store.update_collected_data(session, {
                    "target_appointment_id": candidates[idx]["id"],
                    "current_slot": candidates[idx]["slot"],
                    "full_name": candidates[idx]["patient_name"],
                    "_appointment_selected": True,
                })

    if state == CancelState.AWAITING_CONFIRMATION:
        if text_helpers.is_affirmative(message):
            result.confirmation = True
        elif text_helpers.is_negative(message):
            result.confirmation = False

    return result


# ─── State-Gated Merge ─────────────────────────────────────────────────────

def _merge(session: CallSession, extraction: ExtractionResult, allowed_fields: set, message: str = ""):
    """Merge extraction result into session collected_data, only for allowed fields."""
    updates = {}

    # Flow lock: only allow intent change if explicitly requested via the flag
    if extraction.intent:
        current = _get_active_intent(session)
        if current in ("booking", "reschedule", "cancel"):
            # Only switch workflow if LLM explicitly flagged a switch request
            if extraction.explicit_intent_switch_requested and extraction.intent != current:
                if _is_explicit_workflow_change(message, current):
                    session.intent = extraction.intent
        elif extraction.intent in ("booking", "reschedule", "cancel", "smalltalk", "unknown"):
            session.intent = extraction.intent

    if extraction.full_name and "full_name" in allowed_fields:
        # Sanitize: reject if not name-like
        clean_name = extraction.full_name.strip()
        clean_name = re.sub(r"\s+", " ", clean_name).strip()
        # Only accept if it looks like a real name (alphabetic + spaces + digits, reasonable length)
        if clean_name and len(clean_name) >= 2 and all(c.isalpha() or c == ' ' or c.isdigit() for c in clean_name):
            updates["full_name"] = clean_name
            mem.set_field(session, "full_name", clean_name)
            mem.confirm_field(session, "full_name")
    if extraction.phone and "phone" in allowed_fields:
        # Sanitize: extract only digits from phone
        digits_only = re.sub(r"\D", "", extraction.phone)
        if digits_only and len(digits_only) >= 7:
            updates["phone"] = digits_only
            mem.set_field(session, "phone", digits_only)
            mem.confirm_field(session, "phone")
    if extraction.preferred_slot_or_date and "preferred_slot_or_date" in allowed_fields:
        slot = extraction.preferred_slot_or_date
        all_offered = store.get_offered_slots(session)
        if all_offered and any(slot == s or s.startswith(slot) for s in all_offered):
            matched = next((s for s in all_offered if slot == s or s.startswith(slot)), slot)
            updates["preferred_slot_or_date"] = matched
        else:
            normalized = normalize_natural_slot(slot) or slot
            updates["preferred_slot_or_date"] = normalized
        mem.set_field(session, "preferred_slot_or_date", updates.get("preferred_slot_or_date", slot))
        mem.confirm_field(session, "preferred_slot_or_date")
    if extraction.doctor_name:
        updates["doctor_name"] = extraction.doctor_name
    if extraction.insurance_provider:
        updates["insurance_provider"] = extraction.insurance_provider
    if extraction.symptoms:
        existing = store.get_collected_data(session).get("symptoms", [])
        updates["symptoms"] = list(set(existing + extraction.symptoms))
    if extraction.notes:
        updates["notes"] = extraction.notes
    if extraction.confirmation is not None and "confirmation" in allowed_fields:
        updates["confirmation"] = extraction.confirmation
    if extraction.intent:
        # already handled above with flow lock
        pass

    if updates:
        store.update_collected_data(session, updates)


# ─── Triage ─────────────────────────────────────────────────────────────────

def _run_triage(session: CallSession, message: str, extraction: ExtractionResult):
    combined = message
    if extraction.symptoms:
        combined += " " + " ".join(extraction.symptoms)
    if extraction.urgency_signals:
        combined += " " + " ".join(extraction.urgency_signals)
    urgency, signals = triage_svc.evaluate_urgency(combined)
    if urgency.value == "high":
        session.urgency_level = "high"
        store.update_collected_data(session, {"urgency_signals": signals})
    elif urgency.value == "medium" and session.urgency_level == "none":
        session.urgency_level = "medium"
    return urgency


# ─── Smalltalk / Side Questions ────────────────────────────────────────────

def _handle_smalltalk(message: str, session: CallSession) -> Optional[str]:
    """Handle side questions and smalltalk. Returns response if handled, None otherwise."""
    lower = message.lower().strip()
    collected = store.get_collected_data(session)

    # Smalltalk
    if mem.detect_smalltalk(message):
        responses = [
            "I'm ClinicFlow's virtual receptionist. I'm here to help you with appointment scheduling.",
            "I'm the clinic's AI assistant. I can help you book, reschedule, or cancel appointments.",
        ]
        smalltalk = responses[hash(str(session.id)) % len(responses)]
        pending = _ask_for_field(session)
        if pending:
            smalltalk += f" {pending}"
        return smalltalk

    # Name query
    if mem.detect_name_query(message):
        name = collected.get("full_name")
        status = mem.get_field_status(session, "full_name")
        if status == "confirmed":
            return f"Your name on file is {name}."
        elif status == "tentative":
            return f"I currently have your name as {name}, but I haven't fully confirmed it yet. Is that correct?"
        else:
            return "I don't have your name on file yet. Could you please tell me your full name?"

    # Appointment query — answer from DB if available
    if mem.detect_appointment_query(message):
        current_slot = collected.get("current_slot")
        if current_slot:
            return f"Your current appointment is scheduled for {current_slot}."
        phone = collected.get("phone")
        return "I don't have an appointment on file for you yet. Could you provide the phone number linked to your appointment?"

    # State query
    if mem.detect_state_query(message):
        fields = mem.get_all_tracked_fields(session)
        known = [f"{k}: {v['value']}" for k, v in fields.items() if v["status"] != "missing"]
        if known:
            return "Here's what I have so far: " + ", ".join(known) + "."
        return "I don't have any information recorded yet. How can I help you today?"

    return None


# ─── Field Ask Helpers ─────────────────────────────────────────────────────

def _ask_for_field(session: CallSession) -> Optional[str]:
    """Return the prompt for the next field we need, based on current state."""
    state = session.workflow_state
    collected = store.get_collected_data(session)
    intent = session.session_type or "booking"

    if intent == "booking":
        if state in (BookingState.GREETING, BookingState.AWAITING_NAME) and not collected.get("full_name"):
            return "Could you please tell me your full name?"
        if state == BookingState.AWAITING_PHONE and not collected.get("phone"):
            return "What's the best phone number to reach you?"
        if state == BookingState.AWAITING_SLOT_SELECTION and not collected.get("preferred_slot_or_date"):
            return "Could you select an available slot?"

    if intent == "reschedule":
        if state == RescheduleState.AWAITING_IDENTIFIER and not collected.get("phone"):
            return "Could you please provide the phone number linked to your appointment?"
        if state == RescheduleState.AWAITING_APPOINTMENT_SELECTION:
            return "Please choose an appointment by number."

    if intent == "cancel":
        if state == CancelState.AWAITING_IDENTIFIER and not collected.get("phone"):
            return "Could you please provide the phone number linked to your appointment?"
        if state == CancelState.AWAITING_APPOINTMENT_SELECTION:
            return "Please choose an appointment by number."

    return None


# ─── Correction Handling ───────────────────────────────────────────────────

def _try_correction(message: str, session: CallSession) -> Optional[tuple[str, str]]:
    """Detect and handle correction phrases. Returns (field, prompt) or None."""
    lower = message.lower().strip()

    patterns = {
        "full_name": [
            "that's not my name", "not my name", "wrong name", "incorrect name",
            "my name is not", "you got my name wrong", "that's not me", "not me",
        ],
        "phone": [
            "that's not my number", "not my number", "wrong number", "incorrect number",
            "my number is not", "you got my number wrong", "wrong phone",
        ],
        "preferred_slot_or_date": [
            "that's not the right time", "wrong time", "wrong slot", "not that slot",
            "i meant", "not that date", "different time", "different slot",
        ],
        "appointment_id": [
            "not this appointment", "not that appointment", "wrong appointment",
            "different appointment", "not the one", "not this one", "the other one",
            "use a different appointment",
        ],
    }

    prompts = {
        "full_name": "I apologize for the confusion. Could you please tell me your correct full name?",
        "phone": "I apologize for the confusion. Could you please provide your correct phone number?",
        "preferred_slot_or_date": "I apologize for the confusion. Could you select the correct available slot?",
        "appointment_id": "",
    }

    for field, pats in patterns.items():
        for pat in pats:
            if pat in lower:
                mem.set_correction_target(session, field)
                mem.dispute_field(session, field)
                mem.clear_field(session, field)
                return field, prompts.get(field, "")

    natural_corrections = {
        "full_name": [r"(?:actually|no,)\s+(?:my name is|my correct name is|i'm)"],
        "phone": [r"(?:actually|no,)\s+(?:my number is|my phone is)"],
    }
    for field, pats in natural_corrections.items():
        for pat in pats:
            if re.search(pat, lower):
                mem.set_correction_target(session, field)
                mem.dispute_field(session, field)
                mem.clear_field(session, field)
                return field, prompts.get(field, "")

    return None


def _check_correction_in_progress(message: str, session: CallSession) -> Optional[ExtractionResult]:
    """Handle an in-progress correction flow. Returns ExtractionResult or None."""
    correction_target = mem.get_correction_target(session)
    if not correction_target:
        return None

    result = ExtractionResult()

    if correction_target == "full_name":
        name = text_helpers.extract_name(message) or text_helpers.extract_name_simple(message)
        if name:
            cleaned = name.replace("actually ", "").replace("Actually ", "")
            result.full_name = cleaned
            mem.set_field(session, "full_name", cleaned)
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


# ─── Intent Detection ──────────────────────────────────────────────────────

def detect_intent(message: str) -> Optional[str]:
    """Lightweight keyword-based intent detection for unified sessions.
    
    Returns one of: 'booking', 'reschedule', 'cancel', 'smalltalk', or None (unknown).
    None means the message is generic and does not clearly indicate a workflow intent.
    """
    lower = message.lower().strip()

    # Check for smalltalk / pure greetings first
    if _is_pure_greeting_message(lower) or _is_smalltalk(lower):
        return "smalltalk"

    for kw in _CANCEL_KEYWORDS:
        if kw in lower:
            return "cancel"

    for kw in _RESCHEDULE_KEYWORDS:
        if kw in lower:
            return "reschedule"

    for kw in _BOOKING_KEYWORDS:
        if kw in lower:
            return "booking"

    # No clear intent detected
    return None


def _is_pure_greeting_message(text: str) -> bool:
    """Check if the message is a pure greeting with no workflow intent."""
    words = text.strip().lower().split()
    if not words:
        return True
    clean = " ".join(w.strip(",.!?") for w in words)
    if clean in _GREETING_WORDS:
        return True
    if clean.startswith("hi ") or clean.startswith("hello ") or clean.startswith("hey "):
        return False  # May contain intent after greeting
    if len(words) <= 3 and all(w in _GREETING_WORDS or w in {"there", "how", "are", "you", "good", "morning", "afternoon", "evening", "nice", "meet", "to", "see"} for w in words):
        return True
    return False


def _is_smalltalk(text: str) -> bool:
    """Check if the message is smalltalk without workflow intent."""
    lower = text.lower().strip()
    smalltalk_patterns = [
        "how are you", "how's it going", "what's up", "good morning", "good afternoon", "good evening",
        "nice to meet you", "pleasure to meet", "thanks for help", "thank you", "appreciate it",
        "how's your day", "weather", "who are you", "what can you do",
    ]
    return any(pat in lower for pat in smalltalk_patterns)


# ─── Response Generation ───────────────────────────────────────────────────

def _build_response_context(session: CallSession, state: str, fallback_msg: str, last_msg: str = "") -> dict:
    """Build context dict for AI response generation."""
    collected = store.get_collected_data(session)
    intent = session.session_type or "booking"
    goals = BOOKING_GOALS if intent == "booking" else RESCHEDULE_GOALS if intent == "reschedule" else CANCEL_GOALS

    missing_fields = []
    if intent == "booking":
        if state in (BookingState.GREETING, BookingState.AWAITING_NAME) and not collected.get("full_name"):
            missing_fields.append("full_name")
        if state == BookingState.AWAITING_PHONE and not collected.get("phone"):
            missing_fields.append("phone")
        if state == BookingState.AWAITING_REASON and not collected.get("reason_for_visit"):
            missing_fields.append("reason_for_visit")
        if state == BookingState.AWAITING_SLOT_SELECTION and not collected.get("preferred_slot_or_date"):
            missing_fields.append("preferred_slot_or_date")
        if state == BookingState.AWAITING_CONFIRMATION and collected.get("confirmation") is None:
            missing_fields.append("confirmation")
    elif intent == "reschedule":
        if state == RescheduleState.AWAITING_IDENTIFIER:
            if not collected.get("phone"):
                missing_fields.append("phone")
        elif state == RescheduleState.AWAITING_APPOINTMENT_SELECTION and not collected.get("target_appointment_id"):
            missing_fields.append("target_appointment_id")
        elif state == RescheduleState.AWAITING_NEW_SLOT and not collected.get("preferred_slot_or_date"):
            missing_fields.append("preferred_slot_or_date")
        elif state == RescheduleState.AWAITING_CONFIRMATION and collected.get("confirmation") is None:
            missing_fields.append("confirmation")
    elif intent == "cancel":
        if state == CancelState.AWAITING_IDENTIFIER:
            if not collected.get("phone"):
                missing_fields.append("phone")
        elif state == CancelState.AWAITING_APPOINTMENT_SELECTION and not collected.get("target_appointment_id"):
            missing_fields.append("target_appointment_id")
        elif state == CancelState.AWAITING_CONFIRMATION and collected.get("confirmation") is None:
            missing_fields.append("confirmation")

    return {
        "goal": goals.get(state, "continue_conversation"),
        "state": state,
        "known_fields": collected,
        "missing_fields": missing_fields,
        "urgency_level": session.urgency_level,
        "assistant_goal": goals.get(state, "continue_conversation"),
        "fallback_template": fallback_msg,
        "last_user_message": last_msg,
        "active_workflow": intent,
    }


def _generate_static_response(db: DBSession, session: CallSession, state: str, collected: dict) -> str:
    """Generate a static response for the current state (no LLM)."""
    intent = session.session_type or "booking"
    name = collected.get("full_name", "")

    if intent == "booking":
        if state in (BookingState.GREETING, BookingState.AWAITING_NAME) and not collected.get("full_name"):
            return BOOKING_ASK.get(state, "Could you please tell me your full name?")
        if state == BookingState.AWAITING_PHONE:
            return f"Thank you, {name}. What's the best phone number to reach you?" if name else "What's the best phone number to reach you?"
        if state == BookingState.AWAITING_REASON:
            return "Thanks. What's the reason for your visit today?"
        if state == BookingState.AWAITING_SLOT_SELECTION:
            offered = store.get_offered_slots(session)
            if not offered:
                slots = avail_svc.get_available_slots(db)
                store.update_offered_slots(session, slots)
                offered = slots
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
            return f"Here are the available slots for this week:\n{slot_list}\n\nWhich one works best for you?"
        if state == BookingState.AWAITING_CONFIRMATION:
            slot = collected.get("preferred_slot_or_date", "")
            return (
                f"Great! Here's a summary of your booking:\n"
                f"- Name: {name}\n"
                f"- Phone: {collected.get('phone', '')}\n"
                f"- Preferred Slot: {format_slot_for_speech(slot)}\n\n"
                f"Shall I book this appointment for you?"
            )
        if state == BookingState.COMPLETED:
            slot = collected.get("preferred_slot_or_date", "")
            return f"Perfect! Your appointment has been booked for {format_slot_for_speech(slot)}. We'll send a reminder before your visit. Is there anything else I can help with?"

    if intent == "reschedule":
        if state == RescheduleState.AWAITING_IDENTIFIER and not collected.get("phone"):
            return RESCHEDULE_ASK.get(state)
        if state == RescheduleState.AWAITING_APPOINTMENT_SELECTION:
            candidates = collected.get("_all_appointments", [])
            if candidates:
                appt_list = "\n".join(f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(candidates))
                return f"Which appointment would you like to reschedule?\n{appt_list}"
            return "Which appointment would you like to reschedule?"
        if state == RescheduleState.AWAITING_NEW_SLOT:
            offered = store.get_offered_slots(session)
            if not offered:
                slots = avail_svc.get_available_slots(db)
                store.update_offered_slots(session, slots)
                offered = slots
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
            return f"Here are the available slots:\n{slot_list}\n\nWhich one works best for you?"
        if state == RescheduleState.AWAITING_CONFIRMATION:
            old_slot = collected.get("current_slot", "")
            new_slot = collected.get("preferred_slot_or_date", "")
            return f"Here's a summary of the change:\n- Current slot: {format_slot_for_speech(old_slot)}\n- New slot: {format_slot_for_speech(new_slot)}\n\nShall I go ahead and reschedule?"
        if state == RescheduleState.COMPLETED:
            new_slot = collected.get("preferred_slot_or_date", "")
            return f"Your appointment has been rescheduled to {format_slot_for_speech(new_slot)}. We'll send a reminder before your visit. Is there anything else I can help with?"

    if intent == "cancel":
        if state == CancelState.AWAITING_IDENTIFIER and not collected.get("phone"):
            return CANCEL_ASK.get(state)
        if state == CancelState.AWAITING_APPOINTMENT_SELECTION:
            candidates = collected.get("_all_appointments", [])
            if candidates:
                appt_list = "\n".join(f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(candidates))
                return f"Which appointment would you like to cancel?\n{appt_list}"
            return "Which appointment would you like to cancel?"
        if state == CancelState.AWAITING_CONFIRMATION:
            current_slot = collected.get("current_slot", "")
            return f"I found your appointment on {format_slot_for_speech(current_slot)}. Are you sure you want to cancel this appointment?"
        if state == CancelState.COMPLETED:
            if collected.get("cancel_declined"):
                return "No problem. Your appointment remains scheduled. Is there anything else I can help with?"
            return "Your appointment has been cancelled. Is there anything else I can help with?"

    return ""


# ─── DB Guardrails ──────────────────────────────────────────────────────────

def _check_duplicate_booking(db: DBSession, full_name: str, phone: str) -> Optional[dict]:
    """Check if a patient with matching name and phone already has an upcoming appointment.
    Returns the existing appointment details or None."""
    existing = apt_svc.find_existing_appointment_by_name_phone(db, full_name, phone)
    if existing:
        slot_str = f"{existing.scheduled_date} at {existing.scheduled_time}"
        return {"appointment_id": existing.id, "slot": slot_str}
    return None


def _get_available_slots_filtered(
    db: DBSession, session: CallSession, provider_name: Optional[str] = None
) -> list[str]:
    """Get DB-backed available slots, excluding the current appointment being rescheduled."""
    current_slot = store.get_collected_data(session).get("current_slot", "")
    exclude_id = store.get_collected_data(session).get("target_appointment_id")
    all_slots = avail_svc.get_available_slots(
        db, days=14, provider_name=provider_name, exclude_appointment_id=exclude_id
    )
    if current_slot:
        return [s for s in all_slots if current_slot not in s]
    return all_slots


def _find_nearby_slots(db: DBSession, requested: str, offered: list[str], count: int = 5,
                       provider_name: Optional[str] = None, exclude_appointment_id: Optional[int] = None) -> list[str]:
    """Find nearby real available slots when requested slot is unavailable."""
    try:
        req_date = requested.split(" at ")[0] if " at " in requested else ""
        req_time = requested.split(" at ")[-1] if " at " in requested else ""
        # Strip day name prefix to get actual date
        parts = req_date.split(" ", 1)
        date_str = parts[1] if len(parts) == 2 else parts[0]
    except Exception:
        return offered[:count]

    nearest = avail_svc.find_nearest_available(
        db, date_str, req_time, provider_name=provider_name,
        exclude_appointment_id=exclude_appointment_id, count=count,
    )
    if nearest:
        # Filter out the current slot being rescheduled
        if exclude_appointment_id:
            nearest = [s for s in nearest if s not in offered or s != requested]
        return nearest
    return offered[:count]


def _lookup_appointment(db: DBSession, phone: str):
    """Look up existing upcoming appointment by phone. Returns (appointment, patient_name, current_slot) or (None, None, None)."""
    appointment = apt_svc.find_upcoming_by_phone(db, phone)
    if appointment:
        patient = appointment.patient
        patient_name = patient.full_name if patient else "Patient"
        current_slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
        return appointment, patient_name, current_slot
    return None, None, None


def _lookup_all_appointments(db: DBSession, phone: str) -> list[dict]:
    """Look up ALL upcoming appointments for a phone number. Returns list of dicts."""
    appointments = apt_svc.find_all_upcoming_by_phone(db, phone)
    results = []
    for appt in appointments:
        patient = appt.patient
        results.append({
            "id": appt.id,
            "patient_name": patient.full_name if patient else "Patient",
            "slot": f"{appt.scheduled_date} at {appt.scheduled_time}",
            "reason": appt.reason_for_visit or "General",
        })
    return results


def _track_ask(session: CallSession, field: str) -> int:
    """Track how many times we've asked for the same field. Returns the count."""
    collected = store.get_collected_data(session)
    last_asked = collected.get("_last_asked_field", "")
    count = collected.get("_ask_repeat_count", 0)

    if last_asked == field:
        count += 1
    else:
        count = 1

    store.update_collected_data(session, {
        "_last_asked_field": field,
        "_ask_repeat_count": count,
    })
    return count


def _reset_ask_tracking(session: CallSession):
    """Reset ask tracking when we successfully get a field."""
    store.update_collected_data(session, {
        "_last_asked_field": None,
        "_ask_repeat_count": 0,
    })


def _log_audit(db: DBSession, session: CallSession, user_text: str, state_before: str, ai_result: Optional[ExtractionResult], action: str):
    """Persist an audit log entry for the current turn."""
    try:
        from app.models.conversation_audit_log import ConversationAuditLog
        log_entry = ConversationAuditLog(
            session_id=session.id,
            user_text=user_text,
            workflow_state_before=state_before,
            llm_payload_sent=ai_result.llm_payload_sent if ai_result else None,
            llm_raw_response=ai_result.llm_raw_response if ai_result else None,
            final_action=action
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        import logging
        logging.error(f"Failed to save conversation audit log: {e}")
        db.rollback()


# ─── Unified Conversation Engine ───────────────────────────────────────────

class ConversationEngine:
    """
    Single conversation engine for booking, reschedule, and cancel workflows.
    
    Processes every message through a common pipeline:
    1. Smalltalk / side-question intercept
    2. Correction handling (immediate, same turn)
    3. Deterministic field extraction (fast, no LLM)
    4. State-gated merge (only allowed fields for current state)
    5. State transition (explicit per-intent state machine)
    6. Side effects (DB operations: appointment lookup, create, reschedule, cancel)
    7. Response generation (AI with grounded context, or static template fallback)
    8. Persist + return
    """

    @staticmethod
    def process(db: DBSession, session: CallSession, message: str) -> SendMessageResponse:
        state_before = session.workflow_state
        ai_result = None

        # Determine active intent with proper unknown handling
        intent = session.session_type or session.intent
        if intent not in ("booking", "reschedule", "cancel"):
            intent = "unknown"
            
        logging.debug("ENGINE process: session_type=%s, intent=%s, ws=%s", session.session_type, session.intent, session.workflow_state)

        # ─── SAME-TURN ASYNCHRONOUS WORKFLOW PIVOTING ──────────────────────────
        # Check if the user is declaring their intent now.
        detected_intent = detect_intent(message)
        if detected_intent in ("booking", "reschedule", "cancel"):
            intent = detected_intent
            session.session_type = detected_intent
            session.intent = detected_intent
            store.update_collected_data(session, {"session_intent": detected_intent})
            collected = store.get_collected_data(session)
            if detected_intent == "booking":
                if collected.get("full_name") and collected.get("phone"):
                    session.workflow_state = BookingState.AWAITING_SLOT_SELECTION
                elif collected.get("full_name"):
                    session.workflow_state = BookingState.AWAITING_PHONE
                else:
                    session.workflow_state = BookingState.GREETING
            elif detected_intent == "cancel":
                session.workflow_state = CancelState.AWAITING_IDENTIFIER
            elif detected_intent == "reschedule":
                session.workflow_state = RescheduleState.AWAITING_IDENTIFIER

        # Store user message
        store.append_transcript(session, "user", message)

        # ─── UNKNOWN INTENT TRACK (IDENTITY COLLECTION & LISTENING STATE) ──────
        if intent == "unknown":
            # 0. Handle smalltalk / side questions during identity collection or AWAITING_INTENT_DECLARATION
            smalltalk_response = _handle_smalltalk(message, session)
            if smalltalk_response:
                store.append_transcript(session, "assistant", smalltalk_response)
                store.save_session(db, session)
                _log_audit(db, session, message, state_before, ai_result, "smalltalk_respond")
                return SendMessageResponse(
                    session_id=session.id,
                    assistant_message=smalltalk_response,
                    workflow_state=session.workflow_state or "AWAITING_NAME",
                    collected_data=store.get_collected_data(session),
                    intent="unknown",
                    urgency_level=session.urgency_level,
                    completed=False,
                )

            # Check if we are already in AWAITING_INTENT_DECLARATION state but user didn't declare intent
            if session.workflow_state == "AWAITING_INTENT_DECLARATION":
                resp = f"How can I help you today, {session.patient_name}? You can book a new appointment, reschedule an existing one, or cancel an appointment."
                store.append_transcript(session, "assistant", resp)
                store.save_session(db, session)
                _log_audit(db, session, message, state_before, ai_result, "awaiting_intent_declaration")
                return SendMessageResponse(
                    session_id=session.id,
                    assistant_message=resp,
                    workflow_state="AWAITING_INTENT_DECLARATION",
                    collected_data=store.get_collected_data(session),
                    intent="unknown",
                    urgency_level=session.urgency_level,
                    completed=False,
                )

            # Extract identity fields
            collected = store.get_collected_data(session)
            fallback_result = ExtractionResult()
            
            # Temporary state spoofing so deterministic extract functions work
            if not collected.get("full_name"):
                temp_state = session.workflow_state
                session.workflow_state = BookingState.AWAITING_NAME
                fallback_result = _deterministic_extract_booking(message, session)
                session.workflow_state = temp_state
            elif not collected.get("phone"):
                temp_state = session.workflow_state
                session.workflow_state = BookingState.AWAITING_PHONE
                fallback_result = _deterministic_extract_booking(message, session)
                session.workflow_state = temp_state

            # Fallback to AI extraction if deterministic missed it
            ai_result = None
            if not fallback_result.full_name and not fallback_result.phone:
                context = {
                    "active_workflow": "booking",
                    "known_info": collected,
                    "workflow_state": BookingState.AWAITING_NAME if not collected.get("full_name") else BookingState.AWAITING_PHONE,
                }
                ai_result = ai_assistant_service.analyze_message(message, context)

            # Merge the extracted fields
            extracted = ai_result or fallback_result
            if extracted:
                if extracted.full_name and not collected.get("full_name"):
                    _merge(session, extracted, {"full_name"}, message)
                if extracted.phone and not collected.get("phone"):
                    _merge(session, extracted, {"phone"}, message)

            collected = store.get_collected_data(session)
            
            # 3. Dynamic Intent Gating check after identity collection
            if collected.get("full_name") and collected.get("phone"):
                # Identity is verified!
                from app.models.patient import Patient
                import re
                norm_phone = re.sub(r"\D", "", collected.get("phone"))
                patient_in_db = db.query(Patient).filter(
                    Patient.full_name == collected.get("full_name"),
                    Patient.phone == norm_phone
                ).first()

                session.workflow_state = "AWAITING_INTENT_DECLARATION"
                if patient_in_db:
                    resp = f"Thank you, {session.patient_name}. I've found your profile in our system. How can I help you today? You can book a new appointment, reschedule an existing one, or cancel an appointment."
                else:
                    resp = f"Thank you, {session.patient_name}. I couldn't find your profile in our system. How can I help you today? You can book a new appointment, reschedule an existing one, or cancel an appointment."
            elif not collected.get("full_name"):
                session.workflow_state = "AWAITING_NAME"
                resp = "Hello! I'm ClinicFlow's virtual receptionist. I can help you book, reschedule, or cancel an appointment. Could you please tell me your full name?"
            else:
                session.workflow_state = "AWAITING_PHONE"
                resp = f"Thank you, {collected.get('full_name')}. What's the best phone number to reach you?"

            store.append_transcript(session, "assistant", resp)
            store.save_session(db, session)
            _log_audit(db, session, message, state_before, ai_result, f"transition_to_{session.workflow_state.lower()}")
            return SendMessageResponse(
                session_id=session.id,
                assistant_message=resp,
                workflow_state=session.workflow_state,
                collected_data=store.get_collected_data(session),
                intent="unknown",
                urgency_level=session.urgency_level,
                completed=False,
            )

        # 0. Smalltalk / side-question intercept
        smalltalk_response = _handle_smalltalk(message, session)
        if smalltalk_response:
            store.append_transcript(session, "assistant", smalltalk_response)
            store.save_session(db, session)
            _log_audit(db, session, message, state_before, ai_result, "smalltalk_respond")
            return SendMessageResponse(
                session_id=session.id,
                assistant_message=smalltalk_response,
                workflow_state=session.workflow_state or "greeting",
                collected_data=store.get_collected_data(session),
                intent=session.intent,
                urgency_level=session.urgency_level,
                completed=False,
            )

        # 1. Check correction IN PROGRESS first (before detecting new corrections)
        correction_result = _check_correction_in_progress(message, session)
        if correction_result is not None:
            ai_result = None
            fallback_result = correction_result
        else:
            # 2. Detect new corrections
            correction = _try_correction(message, session)
            if correction:
                field, prompt = correction
                if field == "appointment_id":
                    # User wants to go back to appointment selection
                    collected = store.get_collected_data(session)
                    candidates = collected.get("_all_appointments", [])
                    if candidates:
                        appt_list = "\n".join(
                            f"{i+1}. {a['slot']} — {a['reason']}" for i, a in enumerate(candidates)
                        )
                        prompt = f"No problem. Which appointment would you like to handle?\n{appt_list}"
                        new_state = (
                            RescheduleState.AWAITING_APPOINTMENT_SELECTION
                            if intent == "reschedule"
                            else CancelState.AWAITING_APPOINTMENT_SELECTION
                        )
                        store.update_collected_data(session, {
                            "target_appointment_id": None,
                            "current_slot": None,
                            "_appointment_selected": None,
                        })
                    else:
                        # No candidates stored — go back to identifier
                        new_state = (
                            RescheduleState.AWAITING_IDENTIFIER
                            if intent == "reschedule"
                            else CancelState.AWAITING_IDENTIFIER
                        )
                        prompt = "Could you please provide the phone number linked to your appointment?"
                else:
                    state_map = {
                        "full_name": BookingState.AWAITING_NAME if intent == "booking" else RescheduleState.AWAITING_IDENTIFIER,
                        "phone": BookingState.AWAITING_PHONE if intent == "booking" else RescheduleState.AWAITING_IDENTIFIER,
                        "preferred_slot_or_date": BookingState.AWAITING_SLOT_SELECTION if intent == "booking" else RescheduleState.AWAITING_NEW_SLOT,
                    }
                    new_state = state_map.get(field, session.workflow_state)
                session.workflow_state = new_state
                store.update_collected_data(session, {"workflow_state": new_state})
                store.append_transcript(session, "assistant", prompt)
                store.save_session(db, session)
                _log_audit(db, session, message, state_before, ai_result, "correction_handled")
                return SendMessageResponse(
                    session_id=session.id,
                    assistant_message=prompt,
                    workflow_state=new_state,
                    collected_data=store.get_collected_data(session),
                    intent=session.intent,
                    urgency_level=session.urgency_level,
                    completed=False,
                )

            # 3. Extract fields: deterministic first, AI fallback
            if intent == "booking":
                fallback_result = _deterministic_extract_booking(message, session)
            elif intent == "reschedule":
                fallback_result = _deterministic_extract_reschedule(message, session)
            else:
                fallback_result = _deterministic_extract_cancel(message, session)

            # Only call AI if deterministic didn't find everything needed
            ai_result = _extract_from_ai_if_needed(message, session, intent, fallback_result)

        # 4. State-gated merge
        state = session.workflow_state or "greeting"
        if intent == "booking":
            allowed = BOOKING_MERGE.get(state, set())
        elif intent == "reschedule":
            allowed = RESCHEDULE_MERGE.get(state, set())
        else:
            allowed = CANCEL_MERGE.get(state, set())

        if ai_result:
            _merge(session, ai_result, allowed, message)
            if not _has_field(ai_result, "full_name") and fallback_result.full_name:
                _merge(session, fallback_result, allowed, message)
            if not _has_field(ai_result, "phone") and fallback_result.phone:
                _merge(session, fallback_result, allowed, message)
            if not _has_field(ai_result, "preferred_slot_or_date") and fallback_result.preferred_slot_or_date:
                _merge(session, fallback_result, allowed, message)
            if ai_result.confirmation is None and fallback_result.confirmation is not None:
                _merge(session, fallback_result, allowed, message)
            if ai_result.confirmation is False and fallback_result.confirmation is True:
                _merge(session, fallback_result, allowed, message)
        else:
            _merge(session, fallback_result, allowed, message)

        # Store last message for flow lock context
        session._last_message = message

        # Run triage for booking
        extracted = ai_result or fallback_result
        if intent == "booking" and extracted:
            _run_triage(session, message, extracted)

        # 5. State transition + 6. Side effects
        new_state, fallback_msg = "", ""
        completed = False
        appointment_id = None

        if intent == "booking":
            new_state, fallback_msg, completed, appointment_id = _process_booking(db, session, state)
        elif intent == "reschedule":
            new_state, fallback_msg, completed, appointment_id = _process_reschedule(db, session, state)
        else:
            new_state, fallback_msg, completed, appointment_id = _process_cancel(db, session, state)

        session.workflow_state = new_state
        store.update_collected_data(session, {"workflow_state": new_state})

        # Handle completed state
        if completed or new_state == BookingState.COMPLETED or new_state == RescheduleState.COMPLETED or new_state == CancelState.COMPLETED:
            collected = store.get_collected_data(session)
            # fallback_msg from side-effect processing (e.g., duplicate booking warning)
            # takes priority over the generic static completion response
            msg = fallback_msg or _generate_static_response(db, session, new_state, collected)
            store.append_transcript(session, "assistant", msg)
            store.save_session(db, session)
            _log_audit(db, session, message, state_before, ai_result, f"complete_{intent}")
            return SendMessageResponse(
                session_id=session.id,
                assistant_message=msg,
                workflow_state=new_state,
                collected_data=collected,
                intent=session.intent or intent,
                urgency_level=session.urgency_level,
                appointment_id=appointment_id,
                completed=True,
            )

        # 7. Response generation (AI with grounded context, or static fallback)
        collected = store.get_collected_data(session)
        static_response = _generate_static_response(db, session, new_state, collected)
        fallback_response = fallback_msg or static_response

        # Always build response context and call the LLM, bypassing hardcoded fallback loops.
        # Include the conversation history array. Use fallback_response as fallback if LLM is unavailable or fails.
        wc = _build_response_context(session, new_state, fallback_response, message)
        wc["history"] = store.get_transcript(session)
        
        ai_response = ai_assistant_service.generate_response(wc)
        
        # Post-processing validation: Ensure LLM response contains critical info if present in fallback_response
        use_fallback = False
        if ai_response:
            ai_lower = ai_response.lower()
            if "1." in fallback_response:
                if "1." not in ai_response:
                    use_fallback = True
                else:
                    lines = fallback_response.splitlines()
                    first_slot_line = next((l for l in lines if l.strip().startswith("1. ")), None)
                    if first_slot_line:
                        first_slot_text = first_slot_line.strip().split("1. ", 1)[-1].strip()
                        if first_slot_text not in ai_response:
                            use_fallback = True
            elif "couldn't find" in fallback_response.lower() and not any(k in ai_lower for k in ["couldn't find", "cannot find", "double-check", "no"]):
                use_fallback = True
            elif "already" in fallback_response.lower() and not any(k in ai_lower for k in ["already", "existing"]):
                use_fallback = True

        if ai_response and not use_fallback:
            assistant_message = ai_response
        else:
            assistant_message = fallback_response

        if not assistant_message:
            assistant_message = "I'm ready to help. Could you tell me what you need?"

        # 8. Persist
        store.append_transcript(session, "assistant", assistant_message)
        store.save_session(db, session)

        _log_audit(db, session, message, state_before, ai_result, f"transition_to_{new_state.lower()}")
        return SendMessageResponse(
            session_id=session.id,
            assistant_message=assistant_message,
            workflow_state=new_state,
            collected_data=store.get_collected_data(session),
            intent=session.intent or intent,
            urgency_level=session.urgency_level,
            completed=False,
        )


# ─── AI Extraction (with skip optimization) ────────────────────────────────

def _extract_from_ai_if_needed(
    message: str, session: CallSession, intent: str, fallback: ExtractionResult
) -> Optional[ExtractionResult]:
    """Only call AI extraction if deterministic didn't find what we need."""
    state = session.workflow_state or "greeting"
    collected = store.get_collected_data(session)

    # If deterministic extraction found what this state needs, skip AI
    needed = set()
    if intent == "booking":
        needed = BOOKING_EXTRACT.get(state, set())
    elif intent == "reschedule":
        if state == RescheduleState.AWAITING_IDENTIFIER:
            needed = {"full_name", "phone"}
        elif state == RescheduleState.AWAITING_APPOINTMENT_SELECTION:
            return None  # Appointment selection handled deterministically
        elif state == RescheduleState.AWAITING_NEW_SLOT:
            needed = {"preferred_slot_or_date"}
        elif state == RescheduleState.AWAITING_CONFIRMATION:
            needed = {"confirmation"}
    else:
        if state == CancelState.AWAITING_IDENTIFIER:
            needed = {"phone"}
        elif state == CancelState.AWAITING_APPOINTMENT_SELECTION:
            return None  # Appointment selection handled deterministically
        elif state == CancelState.AWAITING_CONFIRMATION:
            needed = {"confirmation"}

    # Check if deterministic already found everything
    found = set()
    if fallback.full_name and "full_name" in needed:
        found.add("full_name")
    if fallback.phone and "phone" in needed:
        found.add("phone")
    if fallback.preferred_slot_or_date and "preferred_slot_or_date" in needed:
        found.add("preferred_slot_or_date")
    if fallback.confirmation is not None and "confirmation" in needed:
        found.add("confirmation")

    if found >= needed:
        return None  # Skip AI, deterministic found everything

    # Also skip AI for smalltalk-only messages or when only confirmation is needed
    if not needed or (len(needed) == 1 and "confirmation" in needed):
        return None

    # Call AI
    context = {
        "active_workflow": intent,
        "known_info": collected,
        "workflow_state": state,
    }
    return ai_assistant_service.analyze_message(message, context)


def _has_field(result: ExtractionResult, field: str) -> bool:
    """Check if an extraction result has a meaningful value for a field."""
    val = getattr(result, field, None)
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    return bool(val)


# ─── Booking Processing ────────────────────────────────────────────────────

def _process_booking(db: DBSession, session: CallSession, state: str) -> tuple[str, str, bool, Optional[int]]:
    """Process booking state transitions and side effects. Returns (new_state, fallback_msg, completed, appointment_id)."""
    new_state, fallback_msg = _next_booking_state(db, session)
    completed = False
    appointment_id = None

    # Offer slots when entering slot selection (exclude current_slot if reschedule)
    if new_state == BookingState.AWAITING_SLOT_SELECTION and not store.get_offered_slots(session):
        slots = _get_available_slots_filtered(db, session)
        store.update_offered_slots(session, slots)
        slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(slots[:7]))
        fallback_msg = (
            f"Here are the available slots for this week:\n{slot_list}\n\n"
            f"Which one works best for you?"
        )

    # Validate selected slot against availability before confirmation
    if new_state == BookingState.AWAITING_CONFIRMATION:
        collected = store.get_collected_data(session)
        selected = session.selected_slot or collected.get("preferred_slot_or_date", "")
        if selected:
            parts = selected.split(" at ")
            if len(parts) == 2:
                date_part = parts[0].split(" ", 1)[-1] if " " in parts[0] else parts[0]
                time_part = parts[1].split(" —")[0]
                if not avail_svc.is_slot_available(db, date_part, time_part):
                    new_state = BookingState.AWAITING_SLOT_SELECTION
                    session.selected_slot = None
                    store.update_collected_data(session, {"preferred_slot_or_date": None})
                    offered = _get_available_slots_filtered(db, session)
                    store.update_offered_slots(session, offered)
                    slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
                    fallback_msg = f"Sorry, that slot is no longer available. Here are current options:\n{slot_list}\n\nPlease pick one."

    # Complete booking
    if new_state == BookingState.COMPLETED:
        collected = store.get_collected_data(session)
        full_name = collected.get("full_name", "Unknown")
        phone = collected.get("phone", "0000000000")

        # DB guardrail: duplicate booking prevention
        duplicate = _check_duplicate_booking(db, full_name, phone)
        if duplicate:
            slot_str = duplicate["slot"]
            session.status = "completed"
            session.summary_text = summary_svc.generate_summary(db, session)
            msg = (
                f"I see you already have an upcoming appointment on {slot_str}. "
                "You cannot book another one with the same details. "
                "Let me know if you need to reschedule or cancel that appointment."
            )
            store.append_transcript(session, "assistant", msg)
            store.save_session(db, session)
            evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
            return BookingState.COMPLETED, msg, True, duplicate["appointment_id"]

        patient = apt_svc.find_or_create_patient(
            db, full_name=full_name, phone=phone,
            insurance_provider=collected.get("insurance_provider"),
        )
        session.patient_id = patient.id

        slot = session.selected_slot or collected.get("preferred_slot_or_date", "")
        date_str = slot.split(" at ")[0].split(" ")[-1] if " at " in slot else "Unknown"
        time_str = slot.split(" at ")[-1] if " at " in slot else "Unknown"

        appointment = apt_svc.create_appointment(
            db, patient_id=patient.id, scheduled_date=date_str, scheduled_time=time_str,
            reason_for_visit=collected.get("reason_for_visit", "Not specified"),
            doctor_name=collected.get("doctor_name"), notes=collected.get("notes"),
        )
        appointment_id = appointment.id
        session.status = "completed"
        session.summary_text = summary_svc.generate_summary(db, session)
        completed = True

        evt_svc.log_event(db, session.id, EventType.APPOINTMENT_CREATED, {
            "appointment_id": appointment.id, "patient_id": patient.id, "slot": slot,
        })
        evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})

    return new_state, fallback_msg, completed, appointment_id


# ─── Reschedule Processing ─────────────────────────────────────────────────

def _process_reschedule(db: DBSession, session: CallSession, state: str) -> tuple[str, str, bool, Optional[int]]:
    """Process reschedule state transitions and side effects."""
    collected = store.get_collected_data(session)
    new_state = state
    fallback_msg = ""
    completed = False
    appointment_id = None

    if state == RescheduleState.AWAITING_IDENTIFIER:
        phone = collected.get("phone")
        if phone:
            all_appts = _lookup_all_appointments(db, phone)
            if len(all_appts) == 0:
                repeat = _track_ask(session, "reschedule_phone")
                if repeat >= 3:
                    fallback_msg = (
                        "I still cannot find any upcoming appointments linked to that phone number. "
                        "Please double-check the number, or contact the clinic directly for assistance."
                    )
                else:
                    fallback_msg = "I couldn't find any upcoming appointments linked to that number. Could you double-check the phone number?"
            elif len(all_appts) == 1:
                _reset_ask_tracking(session)
                appt = all_appts[0]
                store.update_collected_data(session, {
                    "target_appointment_id": appt["id"],
                    "current_slot": appt["slot"],
                    "full_name": appt["patient_name"],
                    "phone": phone,
                })
                slots = _get_available_slots_filtered(db, session)
                store.update_offered_slots(session, slots)
                slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(slots[:7]))
                new_state = RescheduleState.AWAITING_NEW_SLOT
                fallback_msg = (
                    f"I found your appointment on {format_slot_for_speech(appt['slot'])} "
                    f"({appt['reason']}). "
                    f"Here are the available slots to switch to:\n{slot_list}\n\n"
                    f"Which one works best for you?"
                )
            else:
                _reset_ask_tracking(session)
                appt_list = "\n".join(
                    f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(all_appts)
                )
                new_state = RescheduleState.AWAITING_APPOINTMENT_SELECTION
                fallback_msg = (
                    f"I found {len(all_appts)} upcoming appointment(s) on your account:\n{appt_list}\n\n"
                    f"Which appointment would you like to reschedule? Please enter the number."
                )
                store.update_collected_data(session, {
                    "_all_appointments": all_appts,
                    "phone": phone,
                    "full_name": all_appts[0]["patient_name"],
                })

    elif state == RescheduleState.AWAITING_APPOINTMENT_SELECTION:
        if collected.get("_appointment_selected"):
            _reset_ask_tracking(session)
            appt_id = collected.get("target_appointment_id")
            current_slot = collected.get("current_slot", "")
            slots = _get_available_slots_filtered(db, session)
            store.update_offered_slots(session, slots)
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(slots[:7]))
            new_state = RescheduleState.AWAITING_NEW_SLOT
            fallback_msg = (
                f"Got it — rescheduling your appointment on {format_slot_for_speech(current_slot)}. "
                f"Here are the available slots to switch to:\n{slot_list}\n\n"
                f"Which one works best for you?"
            )
        else:
            candidates = collected.get("_all_appointments", [])
            if candidates:
                appt_list = "\n".join(
                    f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(candidates)
                )
                fallback_msg = f"Please choose an appointment by number:\n{appt_list}"

    elif state == RescheduleState.AWAITING_NEW_SLOT:
        selected = collected.get("preferred_slot_or_date")
        offered = store.get_offered_slots(session)
        if selected and any(selected == s or s.startswith(selected) for s in offered):
            _reset_ask_tracking(session)
            session.selected_slot = selected
            new_state = RescheduleState.AWAITING_CONFIRMATION
        elif selected:
            # User typed a slot not in offered list — check if it's available
            normalized = normalize_natural_slot(selected) or selected
            if avail_svc.is_slot_available(db, normalized.split(" at ")[0].split(" ")[-1] if " at " in normalized else "", normalized.split(" at ")[-1] if " at " in normalized else ""):
                _reset_ask_tracking(session)
                store.update_collected_data(session, {"preferred_slot_or_date": normalized})
                session.selected_slot = normalized
                new_state = RescheduleState.AWAITING_CONFIRMATION
            else:
                # Slot not available — show nearest real alternatives
                exclude_id = collected.get("target_appointment_id")
                nearby = _find_nearby_slots(db, normalized, offered, exclude_appointment_id=exclude_id)
                if nearby:
                    store.update_offered_slots(session, nearby)
                    slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(nearby[:7]))
                    fallback_msg = f"Sorry, that slot isn't available. Here are nearby options:\n{slot_list}\n\nWhich one works best for you?"
                    store.update_collected_data(session, {"preferred_slot_or_date": None})
                else:
                    repeat = _track_ask(session, "reschedule_slot")
                    slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
                    if repeat >= 3:
                        fallback_msg = f"Please type a number from 1 to {len(offered[:7])} to select a slot:\n{slot_list}"
                    else:
                        fallback_msg = f"I didn't recognize that time. Here are the available slots:\n{slot_list}\n\nPlease pick one from the list."
        elif not offered:
            slots = _get_available_slots_filtered(db, session)
            store.update_offered_slots(session, slots)
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(slots[:7]))
            fallback_msg = f"Here are the available slots:\n{slot_list}\n\nWhich one works best for you?"
        else:
            repeat = _track_ask(session, "reschedule_slot")
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(offered[:7]))
            if repeat >= 3:
                fallback_msg = f"Please type a number from 1 to {len(offered[:7])} to select a slot:\n{slot_list}"
            else:
                fallback_msg = f"I didn't recognize that time. Here are the available slots:\n{slot_list}\n\nPlease pick one from the list."

    elif state == RescheduleState.AWAITING_CONFIRMATION:
        if collected.get("confirmation") is True:
            target_id = collected.get("target_appointment_id")
            new_slot = collected.get("preferred_slot_or_date", "")
            date_str = new_slot.split(" at ")[0].split(" ")[-1] if " at " in new_slot else "Unknown"
            time_str = new_slot.split(" at ")[-1] if " at " in new_slot else "Unknown"
            result = apt_svc.reschedule_appointment(db, target_id, date_str, time_str)
            if result:
                appointment_id = result["appointment"].id
                session.status = "completed"
                session.summary_text = summary_svc.generate_summary(db, session)
                evt_svc.log_event(db, session.id, EventType.APPOINTMENT_RESCHEDULED, {
                    "appointment_id": appointment_id, "old_slot": result["old_slot"],
                    "new_slot": new_slot, "phone": collected.get("phone"),
                })
                evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
                new_state = RescheduleState.COMPLETED
                completed = True
            else:
                fallback_msg = "I'm sorry, the reschedule could not be completed. The appointment may no longer exist. Please try again or contact the clinic."
                new_state = RescheduleState.AWAITING_IDENTIFIER
        elif collected.get("confirmation") is False:
            slots = _get_available_slots_filtered(db, session)
            store.update_offered_slots(session, slots)
            store.update_collected_data(session, {"confirmation": None, "preferred_slot_or_date": None})
            slot_list = "\n".join(f"{i+1}. {format_slot_for_speech(s)}" for i, s in enumerate(slots[:7]))
            new_state = RescheduleState.AWAITING_NEW_SLOT
            fallback_msg = f"No problem! Here are the available slots again:\n{slot_list}\n\nWhich one works best for you?"

    return new_state, fallback_msg, completed, appointment_id


# ─── Cancel Processing ─────────────────────────────────────────────────────

def _process_cancel(db: DBSession, session: CallSession, state: str) -> tuple[str, str, bool, Optional[int]]:
    """Process cancel state transitions and side effects."""
    collected = store.get_collected_data(session)
    new_state = state
    fallback_msg = ""
    completed = False
    appointment_id = None

    if state == CancelState.AWAITING_IDENTIFIER:
        phone = collected.get("phone")
        if phone:
            all_appts = _lookup_all_appointments(db, phone)
            if len(all_appts) == 0:
                repeat = _track_ask(session, "cancel_phone")
                if repeat >= 3:
                    fallback_msg = (
                        "I still cannot find any upcoming appointments linked to that phone number. "
                        "Please double-check the number, or contact the clinic directly for assistance."
                    )
                else:
                    fallback_msg = "I couldn't find any upcoming appointments linked to that number. Could you double-check the phone number?"
            elif len(all_appts) == 1:
                _reset_ask_tracking(session)
                appt = all_appts[0]
                store.update_collected_data(session, {
                    "target_appointment_id": appt["id"],
                    "current_slot": appt["slot"],
                    "full_name": appt["patient_name"],
                    "phone": phone,
                })
                new_state = CancelState.AWAITING_CONFIRMATION
                fallback_msg = (
                    f"I found your appointment on {format_slot_for_speech(appt['slot'])} "
                    f"({appt['reason']}). "
                    f"Are you sure you want to cancel this appointment?"
                )
            else:
                _reset_ask_tracking(session)
                appt_list = "\n".join(
                    f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(all_appts)
                )
                new_state = CancelState.AWAITING_APPOINTMENT_SELECTION
                fallback_msg = (
                    f"I found {len(all_appts)} upcoming appointment(s) on your account:\n{appt_list}\n\n"
                    f"Which appointment would you like to cancel? Please enter the number."
                )
                store.update_collected_data(session, {
                    "_all_appointments": all_appts,
                    "phone": phone,
                    "full_name": all_appts[0]["patient_name"],
                })

    elif state == CancelState.AWAITING_APPOINTMENT_SELECTION:
        if collected.get("_appointment_selected"):
            _reset_ask_tracking(session)
            current_slot = collected.get("current_slot", "")
            new_state = CancelState.AWAITING_CONFIRMATION
            fallback_msg = (
                f"Got it — cancelling your appointment on {format_slot_for_speech(current_slot)}. "
                f"Are you sure you want to cancel this appointment?"
            )
        else:
            candidates = collected.get("_all_appointments", [])
            if candidates:
                appt_list = "\n".join(
                    f"{i+1}. {format_slot_for_speech(a['slot'])} — {a['reason']}" for i, a in enumerate(candidates)
                )
                fallback_msg = f"Please choose an appointment by number:\n{appt_list}"

    elif state == CancelState.AWAITING_CONFIRMATION:
        if collected.get("confirmation") is True:
            target_id = collected.get("target_appointment_id")
            result = apt_svc.cancel_appointment(db, target_id)
            if result:
                appointment_id = result.id
                session.status = "completed"
                session.summary_text = summary_svc.generate_summary(db, session)
                evt_svc.log_event(db, session.id, EventType.APPOINTMENT_CANCELLED, {
                    "appointment_id": appointment_id, "phone": collected.get("phone"),
                })
                evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
                new_state = CancelState.COMPLETED
                completed = True
            else:
                fallback_msg = "I'm sorry, the cancellation could not be completed. The appointment may no longer exist. Please try again or contact the clinic."
                new_state = CancelState.AWAITING_IDENTIFIER
        elif collected.get("confirmation") is False:
            new_state = CancelState.COMPLETED
            session.status = "completed"
            store.update_collected_data(session, {"cancel_declined": True})
            session.summary_text = summary_svc.generate_summary(db, session)
            evt_svc.log_event(db, session.id, EventType.SESSION_COMPLETED, {})
            completed = True

    return new_state, fallback_msg, completed, appointment_id
