import sys, os, json
sys.path.insert(0, "D:\\iclinic\\clinicflow\\backend")
os.chdir("D:\\iclinic\\clinicflow\\backend")

from app.llm.client import llm_client

# Test ai_assistant_service directly
from app.services.ai_assistant_service import analyze_message, generate_response

# Test 1: generate_response
ctx = {
    "intent": "booking",
    "state": "awaiting_phone",
    "collected_data": {"full_name": "Aryan"},
    "missing_fields": ["phone"],
    "urgency_level": "none",
    "assistant_goal": "ask_for_phone",
    "fallback_template": "What's the best phone number to reach you?",
}
r = generate_response(ctx)
print("GR result type:", type(r).__name__)
print("GR result length:", len(r) if r else 0)
if r and len(r) > 0:
    print("GR first 50 chars:", r[:50])

# Test 2: analyze_message
ctx2 = {
    "session_type": "booking",
    "intent": "unknown",
    "workflow_state": "awaiting_name",
    "collected_data": {},
    "recent_transcript": [],
}
er = analyze_message("My name is Aryan", ctx2)
if er:
    print("AM result:", er.model_dump())
else:
    print("AM: None")
