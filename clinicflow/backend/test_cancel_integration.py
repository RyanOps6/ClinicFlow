import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.db import Base, engine, get_db
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.orm import Session

# Create all tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def create_test_patient_and_appointment(phone: str):
    """Create a patient and an upcoming appointment to cancel."""
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    
    db = next(get_db())
    try:
        patient = Patient(full_name="John Doe", phone=phone)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        appointment = Appointment(
            patient_id=patient.id,
            appointment_type="general",
            scheduled_date=tomorrow,
            scheduled_time="10:00 AM",
            status="booked",
            reason_for_visit="Annual checkup",
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        return appointment.id
    finally:
        db.close()


def test_cancel_yes():
    print("=== TEST 1: Successful Cancel Flow ===")
    
    # Create test data with unique phone
    apt_id = create_test_patient_and_appointment("5550001")
    print(f"Created appointment {apt_id}")
    
    # Start a cancel session
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    assert resp.status_code == 200, f"Start cancel failed: {resp.text}"
    data = resp.json()
    session_id = data["session_id"]
    print(f"Session ID: {session_id}")
    print(f"Initial: {data['assistant_message']}")
    
    # Provide phone number
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "5550001"})
    assert resp.status_code == 200, f"Phone step failed: {resp.text}"
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    print(f"State: {data['workflow_state']}")
    target_id = data["collected_data"].get("target_appointment_id")
    print(f"Target ID: {target_id}")
    
    assert target_id is not None, "Should have found an appointment to cancel"
    assert target_id == apt_id, f"Target ID should match appointment {apt_id}"
    
    # Confirm cancellation
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "yes"})
    assert resp.status_code == 200, f"Confirm step failed: {resp.text}"
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    print(f"Completed: {data['completed']}")
    print(f"State: {data['workflow_state']}")
    
    assert "cancelled" in data["assistant_message"].lower(), "Expected cancellation success message"
    assert data["completed"] is True, "Session should be completed after cancel"
    
    # Check if appointment is cancelled
    apt_resp = client.get(f"/api/appointments/{target_id}")
    if apt_resp.status_code == 200:
        apt = apt_resp.json()
        print(f"Appointment status: {apt.get('status')}")
        assert apt.get("status") == "cancelled", "Appointment should be marked as cancelled"
    
    print("TEST 1 PASSED\n")
    return target_id


def test_cancel_no():
    print("=== TEST 2: Decline Cancel Flow ===")
    
    # Create test data with unique phone
    apt_id = create_test_patient_and_appointment("5550002")
    print(f"Created appointment {apt_id}")
    
    # Start a cancel session
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    
    # Provide phone number
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "5550002"})
    assert resp.status_code == 200
    data = resp.json()
    target_id = data["collected_data"].get("target_appointment_id")
    print(f"Target ID: {target_id}")
    
    # Decline cancellation
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "no"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    print(f"Completed: {data['completed']}")
    
    assert "remains scheduled" in data["assistant_message"].lower() or "no problem" in data["assistant_message"].lower(), "Expected decline message"
    assert "cancelled" not in data["assistant_message"].lower(), "Should not say cancelled when declined"
    
    # Verify appointment is still active
    apt_resp = client.get(f"/api/appointments/{target_id}")
    if apt_resp.status_code == 200:
        apt = apt_resp.json()
        print(f"Appointment status: {apt.get('status')}")
        assert apt.get("status") in ["booked", "rescheduled"], "Appointment should remain active when declined"
    
    print("TEST 2 PASSED\n")
    return target_id


def test_ambiguous():
    print("=== TEST 3: Ambiguous Confirmation ===")
    
    # Create test data with unique phone
    apt_id = create_test_patient_and_appointment("5550003")
    
    # Start a cancel session
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    
    # Provide phone number
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "5550003"})
    assert resp.status_code == 200
    data = resp.json()
    
    # Ambiguous response
    resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "maybe"})
    assert resp.status_code == 200
    data = resp.json()
    print(f"Assistant: {data['assistant_message']}")
    print(f"State: {data['workflow_state']}")
    
    assert data["workflow_state"] == "cancel_awaiting_confirmation", "Should stay in confirmation state"
    
    print("TEST 3 PASSED\n")


if __name__ == "__main__":
    test_cancel_yes()
    test_cancel_no()
    test_ambiguous()
    print("ALL TESTS PASSED")
