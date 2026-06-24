import json

from sqlalchemy.orm import Session as DBSession

from app.models.event_log import EventLog


def log_event(db: DBSession, session_id: int, event_type: str, payload: dict | None = None):
    event = EventLog(
        session_id=session_id,
        event_type=event_type,
        payload_json=json.dumps(payload) if payload else None,
    )
    db.add(event)
    db.commit()
    return event
