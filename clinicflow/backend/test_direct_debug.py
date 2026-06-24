from app.core.db import SessionLocal
from app.services.conversation_service import handle_message
from app.services import session_store as store

# Start a session
db = SessionLocal()

session = store.create_session(db, "unified", "simulated")
sid = session.id
store.save_session(db, session)

print(f"After start: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")

# Msg1: Booking intent
resp1 = handle_message(db, session, "I want to book an appointment")
print(f"After msg1: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")
print(f"  Response: ws={resp1.workflow_state}, intent={resp1.intent}")

# Msg2: Name
session = store.get_session(db, sid)  # Re-fetch from DB
print(f"Before msg2: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")
resp2 = handle_message(db, session, "My name is Alice Smith")
print(f"After msg2: type={session.session_type}, intent={session.intent}, ws={session.workflow_state}")
print(f"  Response: ws={resp2.workflow_state}, intent={resp2.intent}, name={resp2.collected_data.get('full_name')}")
