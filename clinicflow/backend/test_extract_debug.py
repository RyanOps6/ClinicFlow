from app.services.engine import _deterministic_extract_booking, BookingState
from app.models.call_session import CallSession
from app.services import session_store as store

# Simulate a session in AWAITING_NAME state
session = CallSession()
session.workflow_state = BookingState.AWAITING_NAME
store.update_collected_data(session, {})

result = _deterministic_extract_booking("My name is Alice Smith", session)
print(f"full_name: {result.full_name!r}")
print(f"phone: {result.phone!r}")
