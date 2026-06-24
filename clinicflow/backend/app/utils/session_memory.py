"""Session memory management for reliable conversation state tracking.

Provides field-level confirmation tracking, correction handling, and
smalltalk recovery while keeping the deterministic workflow authoritative.
"""

from typing import Optional

from app.services import session_store as store
from app.models.call_session import CallSession

# Fields that support confirmation/correction tracking
TRACKED_FIELDS = {"full_name", "phone", "reason_for_visit", "preferred_slot_or_date"}


def get_field_status(session: CallSession, field: str) -> str:
    """Return field status: 'confirmed', 'tentative', 'disputed', or 'missing'."""
    collected = store.get_collected_data(session)
    if collected.get(f"{field}_disputed"):
        return "disputed"
    if collected.get(f"{field}_confirmed"):
        return "confirmed"
    if collected.get(field):
        return "tentative"
    return "missing"


def get_value(session: CallSession, field: str) -> Optional[str]:
    """Get field value if it exists, None otherwise."""
    collected = store.get_collected_data(session)
    return collected.get(field)


def set_field(session: CallSession, field: str, value: str, *, confirmed: bool = False):
    """Set a field value with optional confirmation status."""
    updates = {field: value}
    if confirmed:
        updates[f"{field}_confirmed"] = True
        updates[f"{field}_disputed"] = False
    else:
        # If currently missing, mark as tentative (not confirmed)
        collected = store.get_collected_data(session)
        if not collected.get(field):
            updates[f"{field}_confirmed"] = False
    # Clear any pending correction on this field
    updates[f"{field}_disputed"] = False
    store.update_collected_data(session, updates)


def confirm_field(session: CallSession, field: str):
    """Mark a field as confirmed."""
    store.update_collected_data(session, {
        f"{field}_confirmed": True,
        f"{field}_disputed": False,
    })


def dispute_field(session: CallSession, field: str):
    """Mark a field as disputed (user rejected it)."""
    store.update_collected_data(session, {
        f"{field}_disputed": True,
        f"{field}_confirmed": False,
    })


def clear_field(session: CallSession, field: str):
    """Remove a field and its statuses."""
    store.update_collected_data(session, {
        field: None,
        f"{field}_confirmed": False,
        f"{field}_disputed": False,
    })


def set_correction_target(session: CallSession, target: str):
    """Set the current correction target (e.g. 'full_name', 'phone')."""
    store.update_collected_data(session, {"correction_target": target})


def get_correction_target(session: CallSession) -> Optional[str]:
    """Get the current correction target, if any."""
    collected = store.get_collected_data(session)
    return collected.get("correction_target")


def clear_correction_target(session: CallSession):
    """Clear the correction target."""
    store.update_collected_data(session, {"correction_target": None})


def set_pending_confirmation(session: CallSession, field: str):
    """Track what field/thing the assistant asked the user to confirm."""
    store.update_collected_data(session, {"pending_confirmation": field})


def get_pending_confirmation(session: CallSession) -> Optional[str]:
    """Get what the assistant last asked the user to confirm."""
    collected = store.get_collected_data(session)
    return collected.get("pending_confirmation")


def clear_pending_confirmation(session: CallSession):
    """Clear pending confirmation."""
    store.update_collected_data(session, {"pending_confirmation": None})


def get_all_tracked_fields(session: CallSession) -> dict:
    """Return a dict of all tracked fields with their values and statuses."""
    collected = store.get_collected_data(session)
    result = {}
    for field in TRACKED_FIELDS:
        value = collected.get(field)
        status = get_field_status(session, field)
        result[field] = {"value": value, "status": status}
    return result


# Correction detection patterns
_CORRECTION_PATTERNS = {
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


def detect_correction_target(message: str, session: CallSession) -> Optional[str]:
    """Detect if the user is correcting a specific field.

    Returns the field name (e.g. 'full_name') if a correction is detected,
    or None if no specific correction target is identified.
    """
    lower = message.lower().strip()

    for field, patterns in _CORRECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in lower:
                return field

    # Also check for generic "no" / "that's wrong" when a confirmation was pending
    pending = get_pending_confirmation(session)
    if pending and pending in TRACKED_FIELDS:
        if is_generic_rejection(lower):
            return pending

    return None


def is_generic_rejection(text: str) -> bool:
    """Check if text is a generic rejection/negation."""
    rejections = {
        "no", "nope", "nah", "that's wrong", "wrong", "incorrect",
        "that's not right", "not right", "not correct",
    }
    text_lower = text.lower().strip().rstrip(".!,")
    return text_lower in rejections or text_lower.startswith(("no ", "nope ", "nah ", "wrong ", "incorrect "))


# Smalltalk / diversion detection
_SMALLTALK_PATTERNS = [
    "who are you", "what's your name", "what is your name",
    "how are you", "how's it going", "what do you do",
    "are you a robot", "are you human", "are you real",
]

_NAME_QUERY_PATTERNS = [
    "what's my name", "what is my name", "say my name",
    "do you know my name", "what name do you have",
]

_STATE_QUERY_PATTERNS = [
    "what did i tell you", "what do you know", "what do you have",
    "what information", "what info", "what did i say",
]


def detect_smalltalk(message: str) -> bool:
    """Detect if the user is making smalltalk (not part of the workflow)."""
    lower = message.lower().strip()
    return any(pattern in lower for pattern in _SMALLTALK_PATTERNS)


def detect_name_query(message: str) -> bool:
    """Detect if the user is asking about their own name."""
    lower = message.lower().strip()
    return any(pattern in lower for pattern in _NAME_QUERY_PATTERNS)


_APPOINTMENT_QUERY_PATTERNS = [
    "what appointment", "what's my appointment", "what is my appointment",
    "when is my appointment", "when is my next appointment",
    "when am i scheduled", "when is my visit", "what time is my appointment",
    "tell me about my appointment", "do i have an appointment",
    "my appointment details", "appointment details",
]


def detect_appointment_query(message: str) -> bool:
    """Detect if the user is asking about their existing appointment."""
    lower = message.lower().strip()
    return any(pattern in lower for pattern in _APPOINTMENT_QUERY_PATTERNS)


def detect_state_query(message: str) -> bool:
    """Detect if the user is asking what information has been collected."""
    lower = message.lower().strip()
    return any(pattern in lower for pattern in _STATE_QUERY_PATTERNS)
