"""
Comprehensive tests for the unified conversation engine.
Tests booking, reschedule, cancel, duplicate prevention, corrections,
side questions, hallucination prevention, and session UID.
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
    """Remove test patients + appointments by name."""
    import sqlite3
    conn = sqlite3.connect("clinicflow.db")
    for n in names:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (n,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (n,))
    conn.commit()
    conn.close()


# ─── Booking Tests ──────────────────────────────────────────────────────────

def test_booking_happy_path():
    """Full booking flow: name -> phone -> slot -> confirm."""
    s = _start("unified")
    sid = s["session_id"]

    r = _msg(sid, "I want to book an appointment")
    assert r["workflow_state"] in ("greeting", "awaiting_name")
    assert "unified" not in r["intent"] or r["intent"] == "booking"

    r = _msg(sid, "My name is Alice Smith")
    assert r["collected_data"].get("full_name") == "Alice Smith"
    assert r["workflow_state"] == "awaiting_phone"

    r = _msg(sid, "555-999-1234")
    assert "5559991234" in r["collected_data"].get("phone", "")
    assert r["workflow_state"] == "awaiting_slot_selection"

    r = _msg(sid, "1")
    assert r["workflow_state"] == "awaiting_confirmation"

    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert r["appointment_id"] is not None

    print("test_booking_happy_path PASSED")


# ─── Cancel Tests ───────────────────────────────────────────────────────────

def test_cancel_happy_path():
    """Cancel flow: phone -> confirm."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db

    _cleanup(["Cancel Test"])
    db = next(get_db())
    try:
        patient = Patient(full_name="Cancel Test", phone="5550001")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=tomorrow, scheduled_time="11:00",
            status="booked", reason_for_visit="Test",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]

    r = _msg(sid, "I want to cancel my appointment")
    assert r["workflow_state"] == "cancel_awaiting_identifier"

    r = _msg(sid, "5550001")
    assert r["workflow_state"] == "cancel_awaiting_confirmation"

    r = _msg(sid, "yes")
    assert r["completed"] is True

    print("test_cancel_happy_path PASSED")


# ─── Reschedule Tests ──────────────────────────────────────────────────────

def test_reschedule_happy_path():
    """Reschedule flow: phone -> slot -> confirm."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db

    _cleanup(["Reschedule Test"])
    db = next(get_db())
    try:
        patient = Patient(full_name="Reschedule Test", phone="5550002")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=tomorrow, scheduled_time="10:00",
            status="booked", reason_for_visit="Test",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]

    r = _msg(sid, "I need to reschedule my appointment")
    assert r["workflow_state"] == "reschedule_awaiting_identifier"

    r = _msg(sid, "5550002")
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"

    r = _msg(sid, "1")
    assert r["workflow_state"] == "reschedule_awaiting_confirmation"

    r = _msg(sid, "yes")
    assert r["completed"] is True

    print("test_reschedule_happy_path PASSED")


# ─── Duplicate Booking Prevention ───────────────────────────────────────────

def test_duplicate_booking_prevention():
    """Same name + same phone with upcoming appointment -> block."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db

    _cleanup(["Dup Test"])
    db = next(get_db())
    try:
        patient = Patient(full_name="Dup Test", phone="555000100")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=tomorrow, scheduled_time="09:00",
            status="booked", reason_for_visit="Existing",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "I want to book")
    _msg(sid, "Dup Test")
    _msg(sid, "555-000-100")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")

    assert r["completed"] is True
    assert "already" in r["assistant_message"].lower() or "existing" in r["assistant_message"].lower()
    assert r["appointment_id"] is not None

    print("test_duplicate_booking_prevention PASSED")


def test_same_name_different_phone_allows_booking():
    """Same name + different phone -> allow booking."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db

    _cleanup(["Dup Test 2"])
    db = next(get_db())
    try:
        patient = Patient(full_name="Dup Test 2", phone="555000200")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=tomorrow, scheduled_time="09:00",
            status="booked", reason_for_visit="Existing",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "I want to book")
    _msg(sid, "Dup Test 2")
    _msg(sid, "555-999-002")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")

    assert r["completed"] is True
    assert r["appointment_id"] is not None
    assert "already" not in r["assistant_message"].lower()

    print("test_same_name_different_phone_allows_booking PASSED")


# ─── Side Questions ────────────────────────────────────────────────────────

def test_side_question_during_booking():
    """Side question during booking should resume asking for current field."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "book")
    r = _msg(sid, "Alice Smith")
    assert r["workflow_state"] == "awaiting_phone"

    r = _msg(sid, "who are you?")
    assert r["workflow_state"] == "awaiting_phone"
    assert "phone" in r["assistant_message"].lower() or "reach" in r["assistant_message"].lower()

    print("test_side_question_during_booking PASSED")


def test_side_question_during_reschedule():
    """Side question during reschedule should resume asking for phone."""
    s = _start("unified")
    sid = s["session_id"]

    r = _msg(sid, "reschedule")
    assert r["workflow_state"] == "reschedule_awaiting_identifier"

    r = _msg(sid, "what time is it?")
    assert r["workflow_state"] == "reschedule_awaiting_identifier"
    assert "phone" in r["assistant_message"].lower()

    print("test_side_question_during_reschedule PASSED")


# ─── Name Query Tests ──────────────────────────────────────────────────────

def test_name_query_after_collected():
    """After name collected, 'what's my name?' returns stored name."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "book")
    _msg(sid, "Bob Johnson")
    r = _msg(sid, "what's my name?")

    assert "bob johnson" in r["assistant_message"].lower() or "Bob Johnson" in r["assistant_message"]
    assert r["workflow_state"] == "awaiting_phone"

    print("test_name_query_after_collected PASSED")


def test_name_query_before_collected():
    """Before name collected, 'what's my name?' must not hallucinate."""
    s = _start("unified")
    sid = s["session_id"]

    r = _msg(sid, "what's my name?")

    common_names = ["Rachel", "Emily", "Thompson", "Wilson", "Johnson", "Sarah", "Michael"]
    for name in common_names:
        assert name not in r["assistant_message"]

    print("test_name_query_before_collected PASSED")


# ─── Correction Tests ──────────────────────────────────────────────────────

def test_correction_wrong_name():
    """Correction of wrong name should update immediately."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "book")
    _msg(sid, "Wrong Name")

    r = _msg(sid, "that's not my name")
    assert "apologize" in r["assistant_message"].lower() or "correct" in r["assistant_message"].lower() or "name" in r["assistant_message"].lower()

    r = _msg(sid, "Actually my name is Jane Doe")
    assert "jane doe" in r["collected_data"].get("full_name", "").lower()

    print("test_correction_wrong_name PASSED")


def test_correction_wrong_phone():
    """Correction of wrong phone should update immediately."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "book")
    _msg(sid, "Test User")
    _msg(sid, "5550001111")

    r = _msg(sid, "wrong number")
    assert "apologize" in r["assistant_message"].lower() or "correct" in r["assistant_message"].lower() or "phone" in r["assistant_message"].lower()

    r = _msg(sid, "my number is 5559998888")
    assert "5559998888" in r["collected_data"].get("phone", "")

    print("test_correction_wrong_phone PASSED")


# ─── State Protection Tests ────────────────────────────────────────────────

def test_yes_ok_not_name_in_early_state():
    """'ok' should not be treated as a name in early states."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "book")
    r = _msg(sid, "ok")

    assert r["workflow_state"] in ("greeting", "awaiting_name")
    assert r["collected_data"].get("full_name") is None or r["collected_data"].get("full_name") == ""

    print("test_yes_ok_not_name_in_early_state PASSED")


# ─── Session UID Tests ─────────────────────────────────────────────────────

def test_session_uid_created():
    """Every session gets a unique session UID."""
    s1 = _start("unified")
    s2 = _start("unified")

    assert "session_uid" in s1
    assert "session_uid" in s2
    assert s1["session_uid"].startswith("sess_")
    assert s2["session_uid"].startswith("sess_")
    assert s1["session_uid"] != s2["session_uid"]

    print("test_session_uid_created PASSED")


def test_session_uid_in_message_response():
    """Session UID is returned in message responses."""
    s = _start("unified")
    sid = s["session_id"]
    uid = s["session_uid"]

    r = _msg(sid, "hello")
    assert r["session_uid"] == uid

    print("test_session_uid_in_message_response PASSED")


# ─── No Appointment Found Tests ────────────────────────────────────────────

def test_cancel_no_appointment():
    """Cancel with non-existent phone should show error gracefully."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "cancel")
    r = _msg(sid, "555-999-0000")

    assert "couldn't find" in r["assistant_message"].lower() or "double-check" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower()
    assert r["workflow_state"] == "cancel_awaiting_identifier"

    print("test_cancel_no_appointment PASSED")


def test_reschedule_no_appointment():
    """Reschedule with non-existent phone should show error gracefully."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "reschedule")
    r = _msg(sid, "9990009999")

    assert "couldn't find" in r["assistant_message"].lower() or "no" in r["assistant_message"].lower() or "double-check" in r["assistant_message"].lower()
    assert r["workflow_state"] == "reschedule_awaiting_identifier"

    print("test_reschedule_no_appointment PASSED")


def test_conversational_dynamic_gating_chain():
    """Verify Conversational Dynamic Gating chain: hey -> name -> phone -> cancel pivot."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db

    _cleanup(["Aryan"])
    db = next(get_db())
    try:
        patient = Patient(full_name="Aryan", phone="88889999")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id, appointment_type="general",
            scheduled_date=tomorrow, scheduled_time="12:00",
            status="booked", reason_for_visit="Consultation",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]

    # Message 1: "hey" -> Prompts for name
    r1 = _msg(sid, "hey")
    assert r1["workflow_state"] == "AWAITING_NAME"
    assert "name" in r1["assistant_message"].lower()

    # Message 2: "i'm aryan" -> Prompts for phone
    r2 = _msg(sid, "i'm aryan")
    assert r2["workflow_state"] == "AWAITING_PHONE"
    assert "phone" in r2["assistant_message"].lower() or "number" in r2["assistant_message"].lower()

    # Message 3: "88889999" -> Respond "Thank you, Aryan..." and intent stay unknown
    r3 = _msg(sid, "88889999")
    assert r3["workflow_state"] == "AWAITING_INTENT_DECLARATION"
    assert r3["intent"] == "unknown"
    assert "thank you, aryan" in r3["assistant_message"].lower()
    assert "how can i help you today" in r3["assistant_message"].lower()

    # Message 4: "cancel it" -> Must immediately trigger appointment cancellation lookup
    r4 = _msg(sid, "cancel it")
    assert r4["workflow_state"] == "cancel_awaiting_confirmation"
    assert "cancel" in r4["assistant_message"].lower()
    assert r4["completed"] is False

    print("test_conversational_dynamic_gating_chain PASSED")


def test_name_extraction_with_filler():
    """Verify name extraction cleanly handles filler words and phone number sequences."""
    from app.utils.text_helpers import extract_name
    name1 = extract_name("i'm aryan and my number is 66668888")
    assert name1 is not None and name1.lower() == "aryan"
    name2 = extract_name("my name is john and my phone is 555-1234")
    assert name2 is not None and name2.lower() == "john"
    print("test_name_extraction_with_filler PASSED")


def test_dynamic_gating_new_user():
    """Verify gating response for a new user (not in DB) says 'couldn't find your profile'."""
    _cleanup(["New User Test"])
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "hey")
    _msg(sid, "New User Test")
    r = _msg(sid, "555-999-9999")
    
    assert r["workflow_state"] == "AWAITING_INTENT_DECLARATION"
    assert "couldn't find" in r["assistant_message"].lower() or "could not find" in r["assistant_message"].lower()
    print("test_dynamic_gating_new_user PASSED")


def test_dynamic_gating_new_user_pivot_to_book():
    """Verify that a new user (not in DB) who gets gated can pivot to booking successfully."""
    _cleanup(["New User Pivot"])
    s = _start("unified")
    sid = s["session_id"]

    # Step 1: Greeting
    _msg(sid, "hey")
    # Step 2: Name
    _msg(sid, "New User Pivot")
    # Step 3: Phone -> gated
    r = _msg(sid, "555-999-9999")
    assert r["workflow_state"] == "AWAITING_INTENT_DECLARATION"
    
    # Step 4: Pivot to booking
    r_pivot = _msg(sid, "i want to book an appointment")
    assert r_pivot["workflow_state"] == "awaiting_slot_selection"
    assert "here are the available slots" in r_pivot["assistant_message"].lower()
    print("test_dynamic_gating_new_user_pivot_to_book PASSED")


def test_slot_matching_and_formatting():
    """Verify that slot listings are speech-friendly (formatted) and slot matching is precise."""
    s = _start("unified")
    sid = s["session_id"]

    _msg(sid, "I want to book an appointment")
    _msg(sid, "Bob Vance")
    r = _msg(sid, "555-111-2222")
    
    assert r["workflow_state"] == "awaiting_slot_selection"
    # Verify slot output has no year/month/date digits (like 2026-06-24)
    msg = r["assistant_message"]
    import re
    assert not re.search(r'\d{4}-\d{2}-\d{2}', msg), f"Found date string in assistant message: {msg}"
    assert "wednesday at" in msg.lower()

    # Match slot precisely (user types the specific time option rather than number 1)
    # The offered list starts with 9:00, then 10:00. The user specifically requests 10:00.
    r_select = _msg(sid, "Wednesday at 10:00")
    assert r_select["workflow_state"] == "awaiting_confirmation"
    
    # Confirm it matched the 10:00 slot, not the 09:00 slot
    assert "10:00" in r_select["assistant_message"], f"Expected 10:00 in confirmation message, got: {r_select['assistant_message']}"
    assert "09:00" not in r_select["assistant_message"]

    r_confirm = _msg(sid, "yes")
    assert r_confirm["completed"] is True
    print("test_slot_matching_and_formatting PASSED")


# ─── Run All ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_booking_happy_path()
    test_conversational_dynamic_gating_chain()
    test_name_extraction_with_filler()
    test_dynamic_gating_new_user()
    test_dynamic_gating_new_user_pivot_to_book()
    test_slot_matching_and_formatting()
    test_cancel_happy_path()
    test_reschedule_happy_path()
    test_duplicate_booking_prevention()
    test_same_name_different_phone_allows_booking()
    test_side_question_during_booking()
    test_side_question_during_reschedule()
    test_name_query_after_collected()
    test_name_query_before_collected()
    test_correction_wrong_name()
    test_correction_wrong_phone()
    test_yes_ok_not_name_in_early_state()
    test_session_uid_created()
    test_session_uid_in_message_response()
    test_cancel_no_appointment()
    test_reschedule_no_appointment()
    print("\nALL TESTS PASSED")
