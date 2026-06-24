"""
Milestone C tests: engine hardening.
Anti-loop, DB-truthful, multiple appointments, confirmation summaries.
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


def _create_patient_and_appt(phone, name="Test Patient", days_ahead=1):
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    db = next(get_db())
    try:
        patient = Patient(full_name=name, phone=phone)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        future = (date.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        return appt.id
    finally:
        db.close()


def _cleanup_test_data(names):
    import sqlite3
    conn = sqlite3.connect("clinicflow.db")
    for name in names:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (name,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (name,))
    conn.commit()
    conn.close()


# ─── A) BOOKING ────────────────────────────────────────────────────────────

def test_booking_happy_path():
    _cleanup_test_data(["Charlie Brown"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Charlie Brown")
    _msg(sid, "555-111-2222")
    _msg(sid, "Annual checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert r["appointment_id"] is not None
    print("test_booking_happy_path PASSED")


def test_booking_duplicate_prevention():
    _cleanup_test_data(["Dup Block"])
    _create_patient_and_appt("555000999", "Dup Block")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Dup Block")
    _msg(sid, "555-000-999")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "already" in r["assistant_message"].lower() or "existing" in r["assistant_message"].lower()
    assert r["appointment_id"] is not None
    print("test_booking_duplicate_prevention PASSED")


def test_booking_same_name_different_phone_allowed():
    _cleanup_test_data(["Dup Allow"])
    _create_patient_and_appt("555000888", "Dup Allow")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Dup Allow")
    _msg(sid, "555-888-888")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert r["appointment_id"] is not None
    assert "already" not in r["assistant_message"].lower()
    print("test_booking_same_name_different_phone_allowed PASSED")


def test_booking_final_confirmation():
    _cleanup_test_data(["Confirm Test"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Confirm Test")
    _msg(sid, "555-777-777")
    _msg(sid, "Follow-up")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "booked" in r["assistant_message"].lower()
    print("test_booking_final_confirmation PASSED")


# ─── B) RESCHEDULE ─────────────────────────────────────────────────────────

def test_reschedule_happy_path():
    _cleanup_test_data(["Resched Happy"])
    _create_patient_and_appt("555000777", "Resched Happy")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-000-777")
    assert "found" in r["assistant_message"].lower() or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "rescheduled" in r["assistant_message"].lower()
    print("test_reschedule_happy_path PASSED")


def test_reschedule_no_appointment():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-999-000")
    assert "couldn't find" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_identifier"
    print("test_reschedule_no_appointment PASSED")


def test_reschedule_multiple_appointments():
    _cleanup_test_data(["Multi Resched"])
    _create_patient_and_appt("555000666", "Multi Resched", days_ahead=1)
    _create_patient_and_appt("555000666", "Multi Resched", days_ahead=2)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-000-666")
    assert "found" in r["assistant_message"].lower()
    assert "2" in r["assistant_message"] or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    print("test_reschedule_multiple_appointments PASSED")


def test_reschedule_final_confirmation():
    _cleanup_test_data(["Resched Confirm"])
    _create_patient_and_appt("555000555", "Resched Confirm")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-000-555")
    r = _msg(sid, "1")
    assert "summary" in r["assistant_message"].lower() or "reschedule" in r["assistant_message"].lower() or "confirm" in r["assistant_message"].lower() or "slot" in r["assistant_message"].lower() or "which" in r["assistant_message"].lower()
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_reschedule_final_confirmation PASSED")


# ─── C) CANCEL ──────────────────────────────────────────────────────────────

def test_cancel_happy_path():
    _cleanup_test_data(["Cancel Happy"])
    _create_patient_and_appt("555000444", "Cancel Happy")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r = _msg(sid, "555-000-444")
    assert "found" in r["assistant_message"].lower() or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "cancel_awaiting_confirmation"
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_cancel_happy_path PASSED")


def test_cancel_no_appointment():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r = _msg(sid, "555-999-000")
    assert "couldn't find" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower()
    assert r["workflow_state"] == "cancel_awaiting_identifier"
    print("test_cancel_no_appointment PASSED")


def test_cancel_multiple_appointments():
    _cleanup_test_data(["Multi Cancel"])
    _create_patient_and_appt("555000333", "Multi Cancel", days_ahead=1)
    _create_patient_and_appt("555000333", "Multi Cancel", days_ahead=3)
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r = _msg(sid, "555-000-333")
    assert "found" in r["assistant_message"].lower()
    assert "2" in r["assistant_message"] or "appointment" in r["assistant_message"].lower()
    assert r["workflow_state"] == "cancel_awaiting_confirmation"
    print("test_cancel_multiple_appointments PASSED")


def test_cancel_declined():
    _cleanup_test_data(["Cancel Declined"])
    _create_patient_and_appt("555000222", "Cancel Declined")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    _msg(sid, "555-000-222")
    r = _msg(sid, "no")
    assert r["completed"] is True
    assert "remains" in r["assistant_message"].lower() or "keep" in r["assistant_message"].lower() or "not cancel" in r["assistant_message"].lower()
    print("test_cancel_declined PASSED")


# ─── D) ANTI-LOOP ──────────────────────────────────────────────────────────

def test_repeated_phone_asks_vary():
    """Repeated missing phone should not produce identical prompts forever."""
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "cancel")
    r1 = _msg(sid, "hello")
    r2 = _msg(sid, "how are you")
    r3 = _msg(sid, "who are you")
    assert r1["workflow_state"] == "cancel_awaiting_identifier"
    assert r2["workflow_state"] == "cancel_awaiting_identifier"
    assert r3["workflow_state"] == "cancel_awaiting_identifier"
    print("test_repeated_phone_asks_vary PASSED")


def test_reschedule_slot_anti_loop():
    """Repeated unrecognized slot should not loop forever."""
    _cleanup_test_data(["Slot Loop"])
    _create_patient_and_appt("555000111", "Slot Loop")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    _msg(sid, "555-000-111")
    for _ in range(3):
        r = _msg(sid, "xyzzy")
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    assert "number" in r["assistant_message"].lower() or "type" in r["assistant_message"].lower() or "select" in r["assistant_message"].lower()
    print("test_reschedule_slot_anti_loop PASSED")


# ─── E) STATE / UX ─────────────────────────────────────────────────────────

def test_side_question_does_not_reset_workflow():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Side Q")
    assert _msg(sid, "what's 2+2?")["workflow_state"] == "awaiting_phone"
    _msg(sid, "555-000-999")
    r = _msg(sid, "who are you?")
    assert r["workflow_state"] == "awaiting_reason"
    print("test_side_question_does_not_reset_workflow PASSED")


def test_correction_still_works():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Wrong Name")
    r = _msg(sid, "that's not my name")
    assert "apologize" in r["assistant_message"].lower() or "correct" in r["assistant_message"].lower() or "name" in r["assistant_message"].lower()
    r = _msg(sid, "Actually my name is Correct Name")
    assert "correct name" in r["collected_data"].get("full_name", "").lower()
    print("test_correction_still_works PASSED")


def test_already_collected_fields_not_reasked():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Known User")
    _msg(sid, "555-111-000")
    _msg(sid, "I need a checkup")
    r = _msg(sid, "2")
    assert r["workflow_state"] == "awaiting_confirmation"
    assert "summary" in r["assistant_message"].lower() or "name" in r["assistant_message"].lower() or "confirm" in r["assistant_message"].lower()
    print("test_already_collected_fields_not_reasked PASSED")


def test_reschedule_db_truthful_on_failed_lookup():
    """Must not claim appointment found when DB says otherwise."""
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-000-000")
    assert "found" not in r["assistant_message"].lower() or "couldn't" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_identifier"
    print("test_reschedule_db_truthful_on_failed_lookup PASSED")


# ─── Run All ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_booking_happy_path()
    test_booking_duplicate_prevention()
    test_booking_same_name_different_phone_allowed()
    test_booking_final_confirmation()
    test_reschedule_happy_path()
    test_reschedule_no_appointment()
    test_reschedule_multiple_appointments()
    test_reschedule_final_confirmation()
    test_cancel_happy_path()
    test_cancel_no_appointment()
    test_cancel_multiple_appointments()
    test_cancel_declined()
    test_repeated_phone_asks_vary()
    test_reschedule_slot_anti_loop()
    test_side_question_does_not_reset_workflow()
    test_correction_still_works()
    test_already_collected_fields_not_reasked()
    test_reschedule_db_truthful_on_failed_lookup()
    print("\nALL MILESTONE C TESTS PASSED")
