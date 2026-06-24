"""
Tests for Milestone F: Workflow reliability hardening.
Validates flow lock, field-answer guards, cancel/reschedule fences, and confirmation gating.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import SessionLocal, Base, engine
from app.services.availability_service import seed_default_providers

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _ensure_providers():
    db = SessionLocal()
    try:
        seed_default_providers(db)
    finally:
        db.close()


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
    # Also clean up any patients with similar names to avoid conflicts
    all_names = list(names) + [n.replace(" Diff", "").replace(" Block", "").replace(" Happy", "").replace(" Guard", "") for n in names if n]
    for n in all_names:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (n,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (n,))
    # Clean up known leftover test names too
    for leftover in ["Same Name", "Dup Block", "Cancel Happy", "Cancel Fence", "Lock Test", "Lock Resch", "Yes Guard", "Ok Guard", "Intent Guard", "Here Guard", "Confirm Guard", "Phone Guard", "Reason Guard", "Same Name Diff", "Same Name Different Phone"]:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (leftover,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (leftover,))
    conn.commit()
    conn.close()


# ─── A) FLOW LOCK ─────────────────────────────────────────────────────────

def test_flow_lock_cancel_stays_cancel():
    """Once in cancel flow, 'book' does not switch to booking."""
    _cleanup(["Lock Test"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Lock Test", phone="5550001111")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("cancel")
    sid = s["session_id"]
    _msg(sid, "555-000-1111")
    r = _msg(sid, "I want to book instead")
    assert "cancel" in (r.get("intent") or "").lower() or "cancel" in (r.get("workflow_state") or "").lower()
    _cleanup(["Lock Test"])
    print("test_flow_lock_cancel_stays_cancel PASSED")


def test_flow_lock_reschedule_stays_reschedule():
    """Once in reschedule flow, 'cancel' does not switch to cancel."""
    _cleanup(["Lock Resch"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Lock Resch", phone="5550002222")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("reschedule")
    sid = s["session_id"]
    _msg(sid, "555-000-2222")
    r = _msg(sid, "I want to cancel instead")
    assert "reschedule" in (r.get("intent") or "").lower() or "reschedule" in (r.get("workflow_state") or "").lower()
    _cleanup(["Lock Resch"])
    print("test_flow_lock_reschedule_stays_reschedule PASSED")


# ─── B) FIELD-ANSWER GUARD ────────────────────────────────────────────────

def test_yes_not_accepted_as_name():
    """'yes' should not be accepted as a name in booking flow."""
    _cleanup(["Yes Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "yes")
    assert r["collected_data"].get("full_name") is None
    assert "name" in r.get("assistant_message", "").lower() or r["workflow_state"] in ("greeting", "awaiting_name")
    print("test_yes_not_accepted_as_name PASSED")


def test_ok_not_accepted_as_name():
    """'ok' should not be accepted as a name."""
    _cleanup(["Ok Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "ok")
    assert r["collected_data"].get("full_name") is None
    print("test_ok_not_accepted_as_name PASSED")


def test_intent_phrase_not_accepted_as_name():
    """'I want to cancel' should not be accepted as a name."""
    _cleanup(["Intent Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "I want to cancel")
    assert r["collected_data"].get("full_name") is None
    print("test_intent_phrase_not_accepted_as_name PASSED")


def test_here_to_book_not_accepted_as_name():
    """'I'm here to book' should not be accepted as a name."""
    _cleanup(["Here Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "I'm here to book")
    assert r["collected_data"].get("full_name") is None
    print("test_here_to_book_not_accepted_as_name PASSED")


def test_real_name_accepted():
    """'Jack Cole' should be accepted as a name."""
    _cleanup(["Jack Cole"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "Jack Cole")
    assert r["collected_data"].get("full_name") == "Jack Cole"
    _cleanup(["Jack Cole"])
    print("test_real_name_accepted PASSED")


def test_confirmation_only_in_confirmation_state():
    """'yes' should only be treated as confirmation in AWAITING_CONFIRMATION state."""
    _cleanup(["Confirm Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    r = _msg(sid, "yes")
    # In greeting/awaiting_name state, "yes" should NOT be treated as confirmation
    assert r["collected_data"].get("confirmation") is None
    print("test_confirmation_only_in_confirmation_state PASSED")


# ─── C) CANCEL FLOW HARD FENCE ────────────────────────────────────────────

def test_cancel_never_shows_slots():
    """Cancel flow should never offer available slots."""
    _cleanup(["Cancel Fence"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Cancel Fence", phone="5550003333")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("cancel")
    sid = s["session_id"]
    r1 = _msg(sid, "555-000-3333")
    r2 = _msg(sid, "yes")
    # Neither response should contain slot information
    for r in [r1, r2]:
        msg = r.get("assistant_message", "").lower()
        assert "available slot" not in msg, f"Cancel flow showed slots: {msg[:100]}"
        assert "here are the" not in msg or "slot" not in msg, f"Cancel flow showed slot list: {msg[:100]}"

    assert r2.get("completed") is True
    _cleanup(["Cancel Fence"])
    print("test_cancel_never_shows_slots PASSED")


def test_cancel_happy_path_works():
    """Full cancel flow: phone -> confirm -> done."""
    _cleanup(["Cancel Happy"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Cancel Happy", phone="5550004444")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("cancel")
    sid = s["session_id"]
    _msg(sid, "555-000-4444")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert r["appointment_id"] is not None
    _cleanup(["Cancel Happy"])
    print("test_cancel_happy_path_works PASSED")


# ─── D) BOOKING FIELD GUARDS ─────────────────────────────────────────────

def test_booking_phone_rejects_non_phone():
    """When waiting for phone, 'sure' should not be accepted."""
    _cleanup(["Phone Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Phone Guard")
    r = _msg(sid, "sure")
    assert r["collected_data"].get("phone") is None
    assert r["workflow_state"] == "awaiting_phone"
    _cleanup(["Phone Guard"])
    print("test_booking_phone_rejects_non_phone PASSED")


def test_booking_reason_rejects_yes():
    """When waiting for reason, 'yes' should not be accepted."""
    _cleanup(["Reason Guard"])
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Reason Guard")
    _msg(sid, "555-111-9999")
    r = _msg(sid, "yes")
    assert r["collected_data"].get("reason_for_visit") is None
    assert r["workflow_state"] == "awaiting_reason"
    _cleanup(["Reason Guard"])
    print("test_booking_reason_rejects_yes PASSED")


# ─── E) DB GUARDRAILS ─────────────────────────────────────────────────────

def test_duplicate_booking_blocked():
    """Same name + same phone + upcoming appointment -> blocked."""
    _ensure_providers()
    _cleanup(["Dup Block F"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Dup Block F", phone="5550005555")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Dup Block F")
    _msg(sid, "555-000-5555")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "already" in r["assistant_message"].lower() or "existing" in r["assistant_message"].lower()
    _cleanup(["Dup Block F"])
    print("test_duplicate_booking_blocked PASSED")


def test_same_name_different_phone_allows_booking():
    """Same name + different phone -> allows booking."""
    _ensure_providers()
    _cleanup(["Same Name Diff"])
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    from datetime import date, timedelta

    db = next(get_db())
    try:
        future = (date.today() + timedelta(days=10)).isoformat()
        p = Patient(full_name="Same Name Diff", phone="5550006666")
        db.add(p)
        db.commit()
        db.refresh(p)
        appt = Appointment(
            patient_id=p.id, appointment_type="general",
            scheduled_date=future, scheduled_time="10:00",
            status="booked", reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "Same Name Diff")
    _msg(sid, "555-000-7777")
    _msg(sid, "I need a checkup")
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    assert "already" not in r["assistant_message"].lower()
    _cleanup(["Same Name Diff"])
    print("test_same_name_different_phone_allows_booking PASSED")


if __name__ == "__main__":
    test_flow_lock_cancel_stays_cancel()
    test_flow_lock_reschedule_stays_reschedule()
    test_yes_not_accepted_as_name()
    test_ok_not_accepted_as_name()
    test_intent_phrase_not_accepted_as_name()
    test_here_to_book_not_accepted_as_name()
    test_real_name_accepted()
    test_confirmation_only_in_confirmation_state()
    test_cancel_never_shows_slots()
    test_cancel_happy_path_works()
    test_booking_phone_rejects_non_phone()
    test_booking_reason_rejects_yes()
    test_duplicate_booking_blocked()
    test_same_name_different_phone_allows_booking()
    print("\nAll Milestone F tests PASSED!")
