from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

s = client.post("/api/sessions/start", json={"session_type": "unified", "channel": "simulated"}).json()
sid = s["session_id"]

for i, msg in enumerate(["I want to book an appointment", "My name is Alice Smith", "555-999-1234", "1", "yes"], 1):
    r = client.post(f"/api/sessions/{sid}/message", json={"message": msg}).json()
    print(f"Msg{i}: ws={r['workflow_state']}, intent={r['intent']}, type={r.get('session_type')}, name={r['collected_data'].get('full_name')}, phone={r['collected_data'].get('phone')}")
