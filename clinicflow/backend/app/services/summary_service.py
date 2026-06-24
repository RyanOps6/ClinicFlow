import json
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.call_session import CallSession
from app.services import ai_assistant_service


def generate_summary(db: DBSession, session: CallSession) -> str:
    collected = json.loads(session.collected_data_json or "{}")
    session_data = {
        "session_id": session.id,
        "session_type": session.session_type,
        "intent": session.intent,
        "urgency_level": session.urgency_level,
        "collected_data": collected,
    }

    ai_summary = ai_assistant_service.generate_summary(session_data)
    if ai_summary:
        return ai_summary

    return _deterministic_summary(collected, session)


def _deterministic_summary(collected: dict, session: CallSession) -> str:
    name = collected.get("full_name", "Unknown")
    reason = collected.get("reason_for_visit", "Not provided")
    symptoms = collected.get("symptoms", [])
    if session.session_type == "reschedule":
        old_slot = collected.get("current_slot", "Unknown")
        new_slot = collected.get("preferred_slot_or_date", "Not selected")
        return (
            f"- Patient: {name}\n"
            f"- Call Type: Reschedule\n"
            f"- Original Slot: {old_slot}\n"
            f"- New Slot: {new_slot}\n"
            f"- Reason: {reason}\n"
            f"- Urgency: {session.urgency_level}\n"
            f"- Outcome: Appointment rescheduled\n"
        )
    if session.session_type == "cancel":
        current_slot = collected.get("current_slot", "Unknown")
        return (
            f"- Patient: {name}\n"
            f"- Call Type: Cancel\n"
            f"- Cancelled Slot: {current_slot}\n"
            f"- Reason: {reason}\n"
            f"- Urgency: {session.urgency_level}\n"
            f"- Outcome: Appointment cancelled\n"
        )
    slot = collected.get("preferred_slot_or_date", "Not selected")
    return (
        f"- Patient: {name}\n"
        f"- Call Type: {session.session_type}\n"
        f"- Reason: {reason}\n"
        f"- Symptoms: {', '.join(symptoms) if symptoms else 'None reported'}\n"
        f"- Preferred Slot: {slot}\n"
        f"- Urgency: {session.urgency_level}\n"
        f"- Outcome: Session completed\n"
    )
