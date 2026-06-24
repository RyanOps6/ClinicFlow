from app.services.engine import _handle_smalltalk
from app.models.call_session import CallSession
from app.services import session_store as store

session = CallSession()
session.workflow_state = "greeting"
session.intent = "booking"
session.session_type = "booking"
store.update_collected_data(session, {})

result = _handle_smalltalk("My name is Alice Smith", session)
print(f"smalltalk result: {result!r}")
