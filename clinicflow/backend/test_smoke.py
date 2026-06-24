import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.db import Base, engine
from fastapi.testclient import TestClient
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_smoke():
    print("=== SMOKE TEST: Booking and Reschedule still work ===")
    
    # Test booking start
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    assert "How can I help" in data["assistant_message"]
    print(f"Booking session started: {data['session_id']}")
    
    # Test reschedule start
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reschedule" in data["assistant_message"].lower()
    print(f"Reschedule session started: {data['session_id']}")
    
    # Test cancel start
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    assert resp.status_code == 200
    data = resp.json()
    assert "cancel" in data["assistant_message"].lower()
    print(f"Cancel session started: {data['session_id']}")
    
    print("SMOKE TEST PASSED")

if __name__ == "__main__":
    test_smoke()
