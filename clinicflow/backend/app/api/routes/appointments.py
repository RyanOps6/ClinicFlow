from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.schemas.appointment import AppointmentResponse, RescheduleRequest
from app.services import appointment_service as apt_svc
from app.services import event_service as evt_svc
from app.core.constants import EventType

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(db: DBSession = Depends(get_db)):
    return apt_svc.get_appointments(db)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(appointment_id: int, req: RescheduleRequest, db: DBSession = Depends(get_db)):
    appointment = apt_svc.reschedule_appointment(db, appointment_id, req.new_date, req.new_time)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    patient = appointment.patient
    evt_svc.log_event(db, 0, EventType.APPOINTMENT_RESCHEDULED, {
        "appointment_id": appointment.id,
        "new_date": req.new_date,
        "new_time": req.new_time,
    })

    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else None,
        appointment_type=appointment.appointment_type,
        doctor_name=appointment.doctor_name,
        scheduled_date=appointment.scheduled_date,
        scheduled_time=appointment.scheduled_time,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        notes=appointment.notes,
        created_at=appointment.created_at,
    )


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(appointment_id: int, db: DBSession = Depends(get_db)):
    appointment = apt_svc.cancel_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    patient = appointment.patient
    evt_svc.log_event(db, 0, EventType.APPOINTMENT_CANCELLED, {
        "appointment_id": appointment.id,
    })

    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else None,
        appointment_type=appointment.appointment_type,
        doctor_name=appointment.doctor_name,
        scheduled_date=appointment.scheduled_date,
        scheduled_time=appointment.scheduled_time,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        notes=appointment.notes,
        created_at=appointment.created_at,
    )


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment_patch(appointment_id: int, db: DBSession = Depends(get_db)):
    appointment = apt_svc.cancel_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    patient = appointment.patient
    evt_svc.log_event(db, 0, EventType.APPOINTMENT_CANCELLED, {
        "appointment_id": appointment.id,
    })

    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else None,
        appointment_type=appointment.appointment_type,
        doctor_name=appointment.doctor_name,
        scheduled_date=appointment.scheduled_date,
        scheduled_time=appointment.scheduled_time,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        notes=appointment.notes,
        created_at=appointment.created_at,
    )
