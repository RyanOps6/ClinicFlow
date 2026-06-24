from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Start session
r = client.post("/api/sessions/start", json={"session_type": "unified", "channel": "simulated"})
s = r.json()
sid = s["session_id"]
print(f"Session: {sid}")
print(f"Start response: state={s.get('workflow_state')}, intent={s.get('intent')}")

# First message
r = client.post(f"/api/sessions/{sid}/message", json={"message": "I want to book an appointment"})
d = r.json()
print(f"\nMsg 1: state={d['workflow_state']}, intent={d['intent']}")
print(f"  collected: {d['collected_data']}")

# Second message
r = client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Alice Smith"})
d = r.json()
print(f"\nMsg 2: state={d['workflow_state']}, intent={d['intent']}")
print(f"  collected: {d['collected_data']}")
print(f"  name: {d['collected_data'].get('full_name')}")
