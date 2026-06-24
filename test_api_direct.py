from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'clinicflow', 'backend'))
from app.main import app
from app.core.db import Base, engine
client = TestClient(app)

# Start a session
resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
print("START STATUS:", resp.status_code)
print("START BODY:", resp.json())
session_id = resp.json()["session_id"]

# Send a message
resp = client.post(f"/api/sessions/{session_id}/message", json={"message": "hello"})
print("MESSAGE STATUS:", resp.status_code)
print("MESSAGE BODY:", resp.json())
