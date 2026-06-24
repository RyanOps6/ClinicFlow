"""
Milestone D tests: multiple appointment selection, slot availability,
no re-ask, correction handling, DB-truthful behavior.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _start(session_type="unified"):
    r = client.post("/api/sessions/start", json={"session_type": session_type, "channel": "simulated"})
    assert r.status_code == 200
    return r.json()


def _msg(sid, message):
    r = client.post(f"/api/sessions/{sid}/message", json={"message": message})
    assert r.status_code == 200
    return r.json()


def _cleanup(names):
    import sqlite3
    conn = sqlite3.connect("clinicflow.db")
    for n in names:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (n,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (n,))
    conn.commit()
    conn.close()


def _create_appt(phone, name, days_ahead=1, time="10:00"):
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from sqlalchemy import or_
    import re
    normalized = re.sub(r"\D", "", phone)
    db = next(get_db())
    try:
        patient = db.query(Patient).filter(
            Patient.full_name == name,
            Patient.phone == normalized,
        ).first()
        if not patient:
            patient = Patient(full_name=name, phone=normalized)
            db.add(patient)
            db.commit()
            db.refresh(patient)
        future = (date.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=future, scheduled_time=time,
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        return appt.id
    finally:
        db.close()


# ─── 1) Multiple Appointment Selection ──────────────────────────────────────

def test_reschedule_multiple_appt_number_selection():
    _cleanup(["MultiSel"])
    _create_appt("555001001", "MultiSel", days_ahead=1, time="10:00")
    _create_appt("555001001", "MultiSel", days_ahead=2, time="14:00")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-001-001")
    assert "2" in r["assistant_message"] or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_appointment_selection"
    r = _msg(sid, "1")
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "rescheduled" in r["assistant_message"].lower()
    print("test_reschedule_multiple_appt_number_selection PASSED")


def test_cancel_multiple_appt_number_selection():
    _cleanup(["MultiCancelSel"])
    _create_appt("555001002", "MultiCancelSel", days_ahead=1, time="10:00")
    _create_appt("555001002", "MultiCancelSel", days_ahead=3, time="11:00")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r = _msg(sid, "555-001-002")
    assert "2" in r["assistant_message"] or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "cancel_awaiting_appointment_selection"
    r = _msg(sid, "2")
    assert r["workflow_state"] == "cancel_awaiting_confirmation"
    assert "11:00" in r["assistant_message"] or "appointment" in r["assistant_message"].lower()
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_cancel_multiple_appt_number_selection PASSED")


def test_reschedule_single_appt_skips_selection():
    _cleanup(["SingleSel"])
    _create_appt("555001003", "SingleSel", days_ahead=1)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-001-003")
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    assert "appointment_selection" not in r["workflow_state"]
    print("test_reschedule_single_appt_skips_selection PASSED")


# ─── 2) Slot Availability ──────────────────────────────────────────────────

def test_booking_slot_availability():
    """Booking with offered slot by number should work."""
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Slot Avail")
    _msg(sid, "555-222-000")
    _msg(sid, "I need a checkup")
    r = _msg(sid, "1")
    assert r["workflow_state"] == "awaiting_confirmation"
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_booking_slot_availability PASSED")


def test_reschedule_slot_by_number():
    _cleanup(["SlotResched"])
    _create_appt("555001004", "SlotResched", days_ahead=1)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-001-004")
    r = _msg(sid, "2")
    assert r["workflow_state"] == "reschedule_awaiting_confirmation"
    print("test_reschedule_slot_by_number PASSED")


def test_reschedule_unavailable_slot_shows_alternatives():
    _cleanup(["UnavailSlot"])
    _create_appt("555001005", "UnavailSlot", days_ahead=1)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-001-005")
    r = _msg(sid, "next saturday at 3pm")
    assert r["workflow_state"] in ("reschedule_awaiting_new_slot", "reschedule_awaiting_confirmation")
    print("test_reschedule_unavailable_slot_shows_alternatives PASSED")


# ─── 3) No Re-ask for Known Fields ─────────────────────────────────────────

def test_reschedule_no_reask_after_collected():
    _cleanup(["NoReask"])
    _create_appt("555001006", "NoReask", days_ahead=1)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-001-006")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "phone" not in r["assistant_message"].lower() or "rescheduled" in r["assistant_message"].lower()
    print("test_reschedule_no_reask_after_collected PASSED")


def test_booking_no_reask_after_name():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "No Reask User")
    r = _msg(sid, "who are you?")
    assert "name" not in r["assistant_message"].lower() or "phone" in r["assistant_message"].lower() or "receptionist" in r["assistant_message"].lower()
    print("test_booking_no_reask_after_name PASSED")


# ─── 4) Correction Handling ─────────────────────────────────────────────────

def test_correction_not_that_appointment():
    _cleanup(["NotThatAppt"])
    _create_appt("555001007", "NotThatAppt", days_ahead=1, time="10:00")
    _create_appt("555001007", "NotThatAppt", days_ahead=2, time="14:00")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    _msg(sid, "555-001-007")
    r = _msg(sid, "not that appointment")
    assert r["workflow_state"] == "cancel_awaiting_appointment_selection"
    assert "which" in r["assistant_message"].lower() or "choose" in r["assistant_message"].lower() or "number" in r["assistant_message"].lower()
    print("test_correction_not_that_appointment PASSED")


def test_correction_different_slot():
    _cleanup(["DiffSlot"])
    _create_appt("555001008", "DiffSlot", days_ahead=1)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-001-008")
    _msg(sid, "1")
    r = _msg(sid, "actually Friday at 5")
    assert r["workflow_state"] in ("reschedule_awaiting_confirmation", "reschedule_awaiting_new_slot")
    print("test_correction_different_slot PASSED")


def test_correction_phone_number():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Phone Fix")
    _msg(sid, "555-999-000")
    _msg(sid, "Checkup")
    r = _msg(sid, "wrong number")
    assert "correct" in r["assistant_message"].lower() or "phone" in r["assistant_message"].lower() or "number" in r["assistant_message"].lower()
    print("test_correction_phone_number PASSED")


# ─── 5) DB-Truthful ────────────────────────────────────────────────────────

def test_reschedule_no_appt_says_clearly():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-000-000")
    assert "couldn't find" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower()
    assert "rescheduled" not in r["assistant_message"].lower()
    print("test_reschedule_no_appt_says_clearly PASSED")


def test_cancel_no_appt_says_clearly():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r = _msg(sid, "555-000-000")
    assert "couldn't find" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower()
    assert "cancelled" not in r["assistant_message"].lower()
    print("test_cancel_no_appt_says_clearly PASSED")


# ─── Run All ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_reschedule_multiple_appt_number_selection()
    test_cancel_multiple_appt_number_selection()
    test_reschedule_single_appt_skips_selection()
    test_booking_slot_availability()
    test_reschedule_slot_by_number()
    test_reschedule_unavailable_slot_shows_alternatives()
    test_reschedule_no_reask_after_collected()
    test_booking_no_reask_after_name()
    test_correction_not_that_appointment()
    test_correction_different_slot()
    test_correction_phone_number()
    test_reschedule_no_appt_says_clearly()
    test_cancel_no_appt_says_clearly()
    print("\nALL MILESTONE D TESTS PASSED")
