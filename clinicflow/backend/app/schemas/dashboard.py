from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DashboardAppointment(BaseModel):
    id: int
    patient_name: Optional[str] = None
    scheduled_date: str
    scheduled_time: str
    status: str


class DashboardSession(BaseModel):
    id: int
    session_type: str
    status: str
    intent: str
    urgency_level: str
    patient_name: Optional[str] = None
    started_at: Optional[datetime] = None


class DashboardEvent(BaseModel):
    id: int
    session_id: int
    event_type: str
    created_at: Optional[datetime] = None


class DashboardOverview(BaseModel):
    total_appointments: int = 0
    active_sessions: int = 0
    escalations: int = 0
    recent_sessions: list[DashboardSession] = []
    recent_events: list[DashboardEvent] = []
    recent_appointments: list[DashboardAppointment] = []
