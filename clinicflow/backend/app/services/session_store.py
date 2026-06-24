import json
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.call_session import CallSession


def get_session(db: DBSession, session_id: int) -> Optional[CallSession]:
    return db.query(CallSession).filter(CallSession.id == session_id).first()


def create_session(db: DBSession, session_type: str, channel: str = "simulated") -> CallSession:
    session = CallSession(
        session_type=session_type,
        channel=channel,
        status="active",
        intent="unknown",
        workflow_state="greeting",
        collected_data_json="{}",
        transcript_json="[]",
        offered_slots_json="[]",
        urgency_level="none",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def append_transcript(session: CallSession, role: str, content: str):
    transcript = json.loads(session.transcript_json or "[]")
    transcript.append({"role": role, "content": content})
    session.transcript_json = json.dumps(transcript)


def update_collected_data(session: CallSession, data: dict):
    current = json.loads(session.collected_data_json or "{}")
    current.update(data)
    session.collected_data_json = json.dumps(current)


def update_offered_slots(session: CallSession, slots: list[str]):
    session.offered_slots_json = json.dumps(slots)


def get_offered_slots(session: CallSession) -> list[str]:
    return json.loads(session.offered_slots_json or "[]")


def get_collected_data(session: CallSession) -> dict:
    return json.loads(session.collected_data_json or "{}")


def get_transcript(session: CallSession) -> list[dict]:
    return json.loads(session.transcript_json or "[]")


def save_session(db: DBSession, session: CallSession):
    db.commit()
    db.refresh(session)
