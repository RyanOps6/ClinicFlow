from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.models.appointment import Appointment
from app.models.call_session import CallSession
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.schemas.dashboard import (
    DashboardAppointment,
    DashboardEvent,
    DashboardOverview,
    DashboardSession,
)
from app.services.session_store import get_collected_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(db: DBSession = Depends(get_db)):
    total_appointments = db.query(Appointment).count()
    active_sessions = db.query(CallSession).filter(CallSession.status == "active").count()
    escalations = db.query(CallSession).filter(CallSession.urgency_level == "high").count()

    recent_sessions_raw = (
        db.query(CallSession).order_by(CallSession.created_at.desc()).limit(5).all()
    )
    recent_sessions = []
    for s in recent_sessions_raw:
        collected = get_collected_data(s)
        recent_sessions.append(DashboardSession(
            id=s.id,
            session_type=s.session_type,
            status=s.status,
            intent=s.intent,
            urgency_level=s.urgency_level,
            patient_name=collected.get("full_name"),
            started_at=s.started_at,
        ))

    recent_events_raw = (
        db.query(EventLog).order_by(EventLog.created_at.desc()).limit(10).all()
    )
    recent_events = [
        DashboardEvent(id=e.id, session_id=e.session_id, event_type=e.event_type, created_at=e.created_at)
        for e in recent_events_raw
    ]

    recent_appts_raw = (
        db.query(Appointment).order_by(Appointment.created_at.desc()).limit(5).all()
    )
    recent_appointments = []
    for a in recent_appts_raw:
        patient = db.query(Patient).filter(Patient.id == a.patient_id).first()
        recent_appointments.append(DashboardAppointment(
            id=a.id,
            patient_name=patient.full_name if patient else None,
            scheduled_date=a.scheduled_date,
            scheduled_time=a.scheduled_time,
            status=a.status,
        ))

    return DashboardOverview(
        total_appointments=total_appointments,
        active_sessions=active_sessions,
        escalations=escalations,
        recent_sessions=recent_sessions,
        recent_events=recent_events,
        recent_appointments=recent_appointments,
    )
