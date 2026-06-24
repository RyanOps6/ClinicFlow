from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    appointment_type: str
    doctor_name: Optional[str] = None
    scheduled_date: str
    scheduled_time: str
    status: str
    reason_for_visit: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RescheduleRequest(BaseModel):
    new_date: str
    new_time: str
