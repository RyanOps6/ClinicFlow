from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_natural_booking():
    print("=== Test 1: Natural booking with today 4:00pm ===")
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]
    
    for msg in ["I want to book an appointment", "my name is Ryan", "1234567890", "I am not feeling well", "today 4:00pm"]:
        client.post(f"/api/sessions/{sid}/message", json={"message": msg})
    
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "yes"})
    data = r.json()
    assert data["completed"], f"Expected completed, got {data['workflow_state']}"
    assert data["appointment_id"] is not None
    print("PASSED")

def test_ok_confirmation():
    print("=== Test 2: ok as confirmation ===")
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]
    
    for msg in ["I want to book", "Ryan", "1234567890", "I am feeling queued", "today 4:00pm"]:
        client.post(f"/api/sessions/{sid}/message", json={"message": msg})
    
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "ok"})
    data = r.json()
    assert data["completed"], f"Expected completed, got {data['workflow_state']}"
    assert data["appointment_id"] is not None
    print("PASSED")

def test_that_works_confirmation():
    print("=== Test 3: that works as confirmation ===")
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]
    
    for msg in ["I want to book", "Ryan", "1234567890", "sick", "today at 4pm"]:
        client.post(f"/api/sessions/{sid}/message", json={"message": msg})
    
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "that works"})
    data = r.json()
    assert data["completed"], f"Expected completed, got {data['workflow_state']}"
    assert data["appointment_id"] is not None
    print("PASSED")

def test_cancel_regression():
    print("=== Test 4: Cancel flow regression ===")
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    sid = resp.json()["session_id"]
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    data = r.json()
    assert data["workflow_state"].startswith("cancel_"), f"Expected cancel state, got {data['workflow_state']}"
    print("PASSED")

def test_reschedule_regression():
    print("=== Test 5: Reschedule flow regression ===")
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    data = r.json()
    assert data["workflow_state"].startswith("reschedule_"), f"Expected reschedule state, got {data['workflow_state']}"
    print("PASSED")

if __name__ == "__main__":
    test_natural_booking()
    test_ok_confirmation()
    test_that_works_confirmation()
    test_cancel_regression()
    test_reschedule_regression()
    print("ALL TESTS PASSED")
