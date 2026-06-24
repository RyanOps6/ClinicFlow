import enum


class SessionType(str, enum.Enum):
    BOOKING = "booking"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    INTAKE = "intake"
    GENERAL = "general"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


class Intent(str, enum.Enum):
    BOOKING = "booking"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    INTAKE = "intake"
    UNKNOWN = "unknown"


class UrgencyLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventType(str, enum.Enum):
    SESSION_STARTED = "session_started"
    MESSAGE_RECEIVED = "message_received"
    INTENT_DETECTED = "intent_detected"
    FIELD_COLLECTED = "field_collected"
    SLOTS_OFFERED = "slots_offered"
    SLOT_SELECTED = "slot_selected"
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    ESCALATION_TRIGGERED = "escalation_triggered"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


class BookingState(str, enum.Enum):
    GREETING = "greeting"
    AWAITING_NAME = "awaiting_name"
    AWAITING_PHONE = "awaiting_phone"
    AWAITING_REASON = "awaiting_reason"
    AWAITING_SLOT_SELECTION = "awaiting_slot_selection"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"


class RescheduleState(str, enum.Enum):
    AWAITING_IDENTIFIER = "reschedule_awaiting_identifier"
    AWAITING_APPOINTMENT_SELECTION = "reschedule_awaiting_appointment_selection"
    AWAITING_NEW_SLOT = "reschedule_awaiting_new_slot"
    AWAITING_CONFIRMATION = "reschedule_awaiting_confirmation"
    COMPLETED = "completed"


class CancelState(str, enum.Enum):
    AWAITING_IDENTIFIER = "cancel_awaiting_identifier"
    AWAITING_APPOINTMENT_SELECTION = "cancel_awaiting_appointment_selection"
    AWAITING_CONFIRMATION = "cancel_awaiting_confirmation"
    COMPLETED = "completed"
