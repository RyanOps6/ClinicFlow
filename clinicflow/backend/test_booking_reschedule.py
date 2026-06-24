import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.db import Base, engine
from fastapi.testclient import TestClient
from app.main import app

# Reuse existing DB
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_booking_flow():
    print("=== TEST: Booking Flow ===")
    
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    print(f"Started session {session_id}")
    
    # Provide name
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "John Doe"})
    assert resp.status_code == 200
    
    # Provide phone
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "5550005"})
    assert resp.status_code == 200
    
    # Provide reason
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "checkup"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"After reason: {data['assistant_message'][:50]}...")
    
    # Select a slot (extract from message if needed)
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "1"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"After slot selection: {data['assistant_message'][:50]}...")
    
    # Confirm
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "yes"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    
    assert "booked" in data["assistant_message"].lower() or "confirm" in data["assistant_message"].lower(), "Expected booking confirmation"
    assert data["completed"] is True, "Booking should be completed"
    
    print("BOOKING TEST PASSED\n")


def test_reschedule_flow():
    print("=== TEST: Reschedule Flow ===")
    
    # Create a patient + appointment to reschedule
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.core.db import get_db
    
    db = next(get_db())
    try:
        patient = Patient(full_name="Jane Doe", phone="5550006")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt = Appointment(
            patient_id=patient.id,
            appointment_type="general",
            scheduled_date=tomorrow,
            scheduled_time="10:00 AM",
            status="booked",
            reason_for_visit="Checkup",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        print(f"Created appointment {appt.id}")
    finally:
        db.close()
    
    # Start reschedule session
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    print(f"Started reschedule session {session_id}")
    
    # Provide phone
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "5550006"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"After phone: {data['assistant_message'][:60]}...")
    
    # Select new slot
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "1"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"After slot: {data['assistant_message'][:60]}...")
    
    # Confirm
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "yes"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    
    assert "rescheduled" in data["assistant_message"].lower(), "Expected reschedule confirmation"
    assert data["completed"] is True, "Reschedule should be completed"
    
    print("RESCHEDULE TEST PASSED\n")


if __name__ == "__main__":
    test_booking_flow()
    test_reschedule_flow()
    print("ALL BOOKING/RESCHEDULE TESTS PASSED")
