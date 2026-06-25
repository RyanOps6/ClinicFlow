import re

from datetime import datetime
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session as DBSession

from app.models.appointment import Appointment
from app.models.patient import Patient


def find_upcoming_by_phone(db: DBSession, phone: str) -> Optional[Appointment]:
    normalized_phone = re.sub(r"\D", "", phone)
    patients = db.query(Patient).filter(Patient.phone == normalized_phone).all()
    if not patients:
        return None
    patient_ids = [p.id for p in patients]
    today = datetime.now().strftime("%Y-%m-%d")
    return db.query(Appointment).filter(
        and_(
            Appointment.patient_id.in_(patient_ids),
            Appointment.status.in_(["booked", "rescheduled"]),
            Appointment.scheduled_date >= today,
        )
    ).order_by(Appointment.scheduled_date, Appointment.scheduled_time).first()


def find_all_upcoming_by_phone(db: DBSession, phone: str) -> list[Appointment]:
    """Find ALL upcoming appointments for a phone number."""
    normalized_phone = re.sub(r"\D", "", phone)
    patients = db.query(Patient).filter(Patient.phone == normalized_phone).all()
    if not patients:
        return []
    patient_ids = [p.id for p in patients]
    today = datetime.now().strftime("%Y-%m-%d")
    return db.query(Appointment).filter(
        and_(
            Appointment.patient_id.in_(patient_ids),
            Appointment.status.in_(["booked", "rescheduled"]),
            Appointment.scheduled_date >= today,
        )
    ).order_by(Appointment.scheduled_date, Appointment.scheduled_time).all()


def find_upcoming_by_name_phone(db: DBSession, full_name: str, phone: str) -> Optional[Appointment]:
    """Find upcoming appointment matching both name and phone (highest confidence lookup)."""
    normalized_phone = re.sub(r"\D", "", phone)
    patient = db.query(Patient).filter(
        Patient.full_name == full_name,
        Patient.phone == normalized_phone,
    ).first()
    if not patient:
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    return db.query(Appointment).filter(
        and_(
            Appointment.patient_id == patient.id,
            Appointment.status.in_(["booked", "rescheduled"]),
            Appointment.scheduled_date >= today,
        )
    ).order_by(Appointment.scheduled_date, Appointment.scheduled_time).first()


def create_appointment(
    db: DBSession,
    patient_id: int,
    scheduled_date: str,
    scheduled_time: str,
    reason_for_visit: str,
    appointment_type: str = "general",
    doctor_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id,
        appointment_type=appointment_type,
        doctor_name=doctor_name,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        status="booked",
        reason_for_visit=reason_for_visit,
        notes=notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def get_appointments(db: DBSession) -> list[dict]:
    appointments = db.query(Appointment).order_by(Appointment.created_at.desc()).all()
    result = []
    for apt in appointments:
        patient = db.query(Patient).filter(Patient.id == apt.patient_id).first()
        result.append({
            "id": apt.id,
            "patient_id": apt.patient_id,
            "patient_name": patient.full_name if patient else None,
            "appointment_type": apt.appointment_type,
            "doctor_name": apt.doctor_name,
            "scheduled_date": apt.scheduled_date,
            "scheduled_time": apt.scheduled_time,
            "status": apt.status,
            "reason_for_visit": apt.reason_for_visit,
            "notes": apt.notes,
            "created_at": apt.created_at.isoformat() if apt.created_at else None,
        })
    return result


def reschedule_appointment(db: DBSession, appointment_id: int, new_date: str, new_time: str) -> Optional[dict]:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        return None
    old_slot = f"{appointment.scheduled_date} at {appointment.scheduled_time}"
    appointment.scheduled_date = new_date
    appointment.scheduled_time = new_time
    appointment.status = "rescheduled"
    db.commit()
    db.refresh(appointment)
    return {
        "appointment": appointment,
        "old_slot": old_slot,
    }


def cancel_appointment(db: DBSession, appointment_id: int) -> Optional[Appointment]:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        return None
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    return appointment


def find_existing_appointment_by_name_phone(db: DBSession, full_name: str, phone: str) -> Optional[Appointment]:
    """Check if a patient with matching name and phone already has an upcoming appointment."""
    normalized_phone = re.sub(r"\D", "", phone)
    patient = db.query(Patient).filter(
        Patient.full_name == full_name,
        Patient.phone == normalized_phone,
    ).first()
    if not patient:
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    return db.query(Appointment).filter(
        and_(
            Appointment.patient_id == patient.id,
            Appointment.status.in_(["booked", "rescheduled"]),
            Appointment.scheduled_date >= today,
        )
    ).order_by(Appointment.scheduled_date, Appointment.scheduled_time).first()


def find_or_create_patient(db: DBSession, full_name: str, phone: str, insurance_provider: Optional[str] = None) -> Patient:
    normalized_phone = re.sub(r"\D", "", phone)
    patient = db.query(Patient).filter(
        Patient.full_name == full_name,
        Patient.phone == normalized_phone,
    ).first()
    if patient:
        if insurance_provider:
            patient.insurance_provider = insurance_provider
            db.commit()
        return patient
    patient = Patient(
        full_name=full_name,
        phone=normalized_phone,
        insurance_provider=insurance_provider,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
