from fastapi.testclient import TestClient
from app.main import app
from app.core.db import SessionLocal
from app.models.call_session import CallSession

client = TestClient(app)
db = SessionLocal()

s = client.post("/api/sessions/start", json={"session_type": "unified", "channel": "simulated"}).json()
sid = s["session_id"]

session = db.query(CallSession).filter_by(id=sid).first()
print(f"After start: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")

for i, msg in enumerate(["I want to book an appointment", "My name is Alice Smith"], 1):
    r = client.post(f"/api/sessions/{sid}/message", json={"message": msg}).json()
    db.expire_all()  # force refresh
    session = db.query(CallSession).filter_by(id=sid).first()
    print(f"After msg{i}: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")
    print(f"  Response: ws={r['workflow_state']}, intent={r['intent']}, name={r['collected_data'].get('full_name')}")
