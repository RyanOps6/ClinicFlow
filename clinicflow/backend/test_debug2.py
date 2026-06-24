from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

s = client.post("/api/sessions/start", json={"session_type": "unified", "channel": "simulated"}).json()
sid = s["session_id"]

r1 = client.post(f"/api/sessions/{sid}/message", json={"message": "I want to book an appointment"}).json()
print(f"Msg1: state={r1['workflow_state']}, intent={r1['intent']}")

r2 = client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Alice Smith"}).json()
print(f"Msg2: state={r2['workflow_state']}, intent={r2['intent']}")
print(f"Msg2 name: {r2['collected_data'].get('full_name')}")
print(f"Msg2 all collected: {r2['collected_data']}")
