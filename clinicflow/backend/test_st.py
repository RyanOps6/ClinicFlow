from app.services.engine import _is_smalltalk, _is_pure_greeting_message
msg = "My name is Alice Smith"
print(f"is_smalltalk: {_is_smalltalk(msg)}")
print(f"is_pure_greeting: {_is_pure_greeting_message(msg)}")
