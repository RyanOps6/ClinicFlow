from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CorrectionSignals(BaseModel):
    name_correction: bool = False
    phone_correction: bool = False


class ProposedUpdates(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ExtractionResult(BaseModel):
    intent: Optional[str] = None
    explicit_intent_switch_requested: bool = False
    full_name: Optional[str] = None
    phone: Optional[str] = None
    reason_for_visit: Optional[str] = None
    reason_for_cancellation: Optional[str] = None
    preferred_slot_or_date: Optional[str] = None
    doctor_name: Optional[str] = None
    insurance_provider: Optional[str] = None
    symptoms: list[str] = []
    urgency_signals: list[str] = []
    confirmation: Optional[bool] = None
    cancellation_requested: bool = False
    reschedule_requested: bool = False
    correction_signals: CorrectionSignals = CorrectionSignals()
    proposed_updates: ProposedUpdates = ProposedUpdates()
    possible_conflicts: list[str] = []
    notes: Optional[str] = None
    confidence: float = 0.0
    appointment_identifier: Optional[str] = None
    llm_payload_sent: Optional[str] = None
    llm_raw_response: Optional[str] = None


class StartSessionRequest(BaseModel):
    session_type: str = "unified"
    channel: str = "simulated"


class StartSessionResponse(BaseModel):
    session_id: int
    session_uid: str
    assistant_message: str
    workflow_state: str
    collected_data: dict


class SendMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    session_id: int
    session_uid: str = ""
    assistant_message: str
    workflow_state: str
    collected_data: dict
    intent: str
    urgency_level: str
    appointment_id: Optional[int] = None
    completed: bool = False


class SessionSnapshot(BaseModel):
    id: int
    session_uid: str
    session_type: str
    channel: str
    status: str
    intent: str
    workflow_state: Optional[str] = None
    collected_data: dict
    transcript: list[dict]
    offered_slots: list[str]
    selected_slot: Optional[str] = None
    summary_text: Optional[str] = None
    urgency_level: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MessageEntry(BaseModel):
    role: str
    content: str
