from datetime import datetime, timezone

import secrets

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_uid = Column(String(20), unique=True, index=True, nullable=False, default=lambda: f"sess_{secrets.token_hex(6)}")
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    session_type = Column(String, nullable=False, default="general")
    channel = Column(String, nullable=False, default="simulated")
    status = Column(String, nullable=False, default="active")
    intent = Column(String, nullable=True, default="unknown")
    workflow_state = Column(String, nullable=True)
    collected_data_json = Column(Text, nullable=True)
    transcript_json = Column(Text, nullable=True)
    offered_slots_json = Column(Text, nullable=True)
    selected_slot = Column(String, nullable=True)
    summary_text = Column(Text, nullable=True)
    urgency_level = Column(String, nullable=False, default="none")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", backref="call_sessions", lazy="joined")

    @property
    def patient_name(self) -> str:
        import json
        try:
            collected = json.loads(self.collected_data_json) if self.collected_data_json else {}
        except Exception:
            collected = {}
        if collected.get("full_name"):
            return collected["full_name"]
        if self.patient:
            return self.patient.full_name
        return "Patient"

