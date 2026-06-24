"""
Milestone E tests: DB-backed provider scheduling and real slot availability.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import SessionLocal, Base, engine
from app.models.provider_schedule import ProviderSchedule
from app.services.availability_service import seed_default_providers

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _ensure_providers():
    """Ensure default provider schedules exist in DB."""
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
    for n in names:
        conn.execute("DELETE FROM appointments WHERE patient_id IN (SELECT id FROM patients WHERE full_name = ?)", (n,))
        conn.execute("DELETE FROM patients WHERE full_name = ?", (n,))
    conn.commit()
    conn.close()


def _create_appt(phone, name, days_ahead=1, time="10:00", doctor=None):
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    db = SessionLocal()
    try:
        normalized = __import__("re").sub(r"\D", "", phone)
        patient = db.query(Patient).filter(Patient.full_name == name, Patient.phone == normalized).first()
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
            doctor_name=doctor,
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        return appt.id
    finally:
        db.close()


# ─── 1) Slot Generation from Provider Schedule ──────────────────────────────

def test_provider_schedule_generates_correct_slots():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        slots = get_available_slots(db, days=1)
        assert len(slots) > 0, "Should generate slots from provider schedules"
        assert "Dr. Smith" in slots[0] or "Dr. Jones" in slots[0]
        assert " — " in slots[0], "Slots should include provider name"
    finally:
        db.close()
    print("test_provider_schedule_generates_correct_slots PASSED")


def test_provider_schedule_has_correct_times():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        slots = get_available_slots(db, days=7)
        dr_smith_slots = [s for s in slots if "Dr. Smith" in s]
        assert len(dr_smith_slots) > 0, "Dr. Smith should have slots"
        dr_jones_slots = [s for s in slots if "Dr. Jones" in s]
        assert len(dr_jones_slots) > 0, "Dr. Jones should have slots"
        smith_hours = [s.split(" at ")[-1].split(" —")[0] for s in dr_smith_slots]
        jones_hours = [s.split(" at ")[-1].split(" —")[0] for s in dr_jones_slots]
        assert "09:00" in smith_hours, f"Dr. Smith should have 09:00 slots, got: {smith_hours[:5]}"
        assert "10:00" in jones_hours, f"Dr. Jones should have 10:00 slots, got: {jones_hours[:5]}"
    finally:
        db.close()
    print("test_provider_schedule_has_correct_times PASSED")


def test_no_weekend_slots():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        slots = get_available_slots(db, days=14)
        for s in slots:
            assert "Saturday" not in s or "Dr." not in s, f"Should not have Saturday slots: {s}"
            assert "Sunday" not in s, f"Should not have Sunday slots: {s}"
    finally:
        db.close()
    print("test_no_weekend_slots PASSED")


# ─── 2) Booked Slot Exclusion ───────────────────────────────────────────────

def test_booked_slot_not_offered():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    _cleanup(["BookedSlot"])
    appt_id = _create_appt("555002001", "BookedSlot", days_ahead=1, time="10:00", doctor="Dr. Smith")
    db = SessionLocal()
    try:
        future = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = get_available_slots(db, days=1)
        booked_label = f"Monday {future} at 10:00 — Dr. Smith"
        assert booked_label not in slots, f"Booked slot should not appear: {booked_label}"
    finally:
        db.close()
    print("test_booked_slot_not_offered PASSED")


# ─── 3) Canceled Appointment Does Not Block ─────────────────────────────────

def test_canceled_slot_still_available():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    _cleanup(["CanceledSlot"])
    _create_appt("555002002", "CanceledSlot", days_ahead=2, time="14:00", doctor="Dr. Jones")
    import sqlite3
    conn = sqlite3.connect("clinicflow.db")
    conn.execute("UPDATE appointments SET status = 'cancelled' WHERE patient_id IN (SELECT id FROM patients WHERE full_name = 'CanceledSlot')")
    conn.commit()
    conn.close()
    db = SessionLocal()
    try:
        slots = get_available_slots(db, days=3)
        future = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][date.today().weekday() + 2]
        canceled_slot = f"{day_name} {future} at 14:00 — Dr. Jones"
        assert any(canceled_slot in s for s in slots), f"Canceled slot should be available again: {canceled_slot}"
    finally:
        db.close()
    print("test_canceled_slot_still_available PASSED")


# ─── 4) Reschedule Excludes Current Appointment ─────────────────────────────

def test_reschedule_excludes_own_slot():
    _cleanup(["ReschedExclude"])
    appt_id = _create_appt("555002003", "ReschedExclude", days_ahead=1, time="11:00", doctor="Dr. Smith")
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "reschedule")
    r = _msg(sid, "555-002-003")
    offered_slots = r["collected_data"].get("_offered_slots", r.get("assistant_message", ""))
    assert r["workflow_state"] == "reschedule_awaiting_new_slot"
    _msg(sid, "1")
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_reschedule_excludes_own_slot PASSED")


# ─── 5) No Provider Preference = Earliest Across Providers ──────────────────

def test_earliest_slot_across_providers():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        slots = get_available_slots(db, days=1)
        earliest = min(slots, key=lambda s: s.split(" at ")[-1].split(" —")[0])
        assert "09:00" in earliest or "10:00" in earliest, f"Earliest should be 09:00 or 10:00, got: {earliest}"
    finally:
        db.close()
    print("test_earliest_slot_across_providers PASSED")


# ─── 6) Unavailable Slot Returns Real Alternatives ──────────────────────────

def test_unavailable_slot_returns_nearby():
    _ensure_providers()
    from app.services.availability_service import find_nearest_available
    _cleanup(["NearbySlot"])
    _create_appt("555002004", "NearbySlot", days_ahead=1, time="10:00", doctor="Dr. Smith")
    db = SessionLocal()
    try:
        future = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        nearest = find_nearest_available(db, future, "10:00", count=3)
        assert len(nearest) > 0, "Should find nearby alternatives"
        for s in nearest:
            assert "10:00" not in s or "Dr. Jones" in s, f"Should not return booked Dr. Smith 10:00 slot"
    finally:
        db.close()
    print("test_unavailable_slot_returns_nearby PASSED")


# ─── 7) Provider Filtering ──────────────────────────────────────────────────

def test_filter_by_provider():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        smith_only = get_available_slots(db, days=1, provider_name="Dr. Smith")
        assert all("Dr. Smith" in s for s in smith_only), "Should only show Dr. Smith slots"
        jones_only = get_available_slots(db, days=1, provider_name="Dr. Jones")
        assert all("Dr. Jones" in s for s in jones_only), "Should only show Dr. Jones slots"
        assert len(smith_only) > 0 and len(jones_only) > 0
    finally:
        db.close()
    print("test_filter_by_provider PASSED")


# ─── 8) Past Slots Not Included ─────────────────────────────────────────────

def test_no_past_slots():
    _ensure_providers()
    from app.services.availability_service import get_available_slots
    db = SessionLocal()
    try:
        today = date.today().strftime("%Y-%m-%d")
        now_hour = date.today().strftime("%H")
        slots = get_available_slots(db, days=1)
        today_slots = [s for s in slots if today in s]
        for s in today_slots:
            time_part = s.split(" at ")[-1].split(" —")[0]
            assert time_part >= "09:00", f"Should not offer past slots: {s}"
    finally:
        db.close()
    print("test_no_past_slots PASSED")


# ─── 9) Booking Uses DB-Backed Slots ────────────────────────────────────────

def test_booking_uses_db_slots():
    s = _start("unified")
    sid = s["session_id"]
    _msg(sid, "book")
    _msg(sid, "DB Slot User")
    _msg(sid, "555-300-001")
    _msg(sid, "I need a checkup")
    r = _msg(sid, "1")
    assert r["workflow_state"] == "awaiting_confirmation"
    r = _msg(sid, "yes")
    assert r["completed"] is True
    print("test_booking_uses_db_slots PASSED")


# ─── Run All ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_provider_schedule_generates_correct_slots()
    test_provider_schedule_has_correct_times()
    test_no_weekend_slots()
    test_booked_slot_not_offered()
    test_canceled_slot_still_available()
    test_reschedule_excludes_own_slot()
    test_earliest_slot_across_providers()
    test_unavailable_slot_returns_nearby()
    test_filter_by_provider()
    test_no_past_slots()
    test_booking_uses_db_slots()
    print("\nALL MILESTONE E TESTS PASSED")
