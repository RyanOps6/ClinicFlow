from app.services.engine import detect_intent
tests = ["I want to book an appointment", "I want to cancel", "I want to reschedule", "Alice Smith", "555-999-1234"]
for t in tests:
    print(f"{t!r} -> {detect_intent(t)}")
