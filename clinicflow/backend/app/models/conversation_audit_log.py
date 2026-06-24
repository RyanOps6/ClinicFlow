from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.core.db import Base


class ConversationAuditLog(Base):
    __tablename__ = "conversation_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("call_sessions.id"), nullable=False)
    user_text = Column(Text, nullable=False)
    workflow_state_before = Column(String, nullable=True)
    llm_payload_sent = Column(Text, nullable=True)
    llm_raw_response = Column(Text, nullable=True)
    final_action = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
