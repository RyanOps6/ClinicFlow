import sys, os
sys.path.insert(0, "D:\\iclinic\\clinicflow\\backend")
os.chdir("D:\\iclinic\\clinicflow\\backend")

from app.services.ai_assistant_service import generate_response, analyze_message

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
print("generate_response:", repr(r[:100]) if r else "None")

session_ctx = {
    "session_type": "booking",
    "intent": "unknown",
    "workflow_state": "awaiting_name",
    "collected_data": {},
    "recent_transcript": [],
}
er = analyze_message("I'm John Doe", session_ctx)
if er:
    print("analyze_message name:", er.full_name)
    print("analyze_message intent:", er.intent)
    print("analyze_message confidence:", er.confidence)
else:
    print("analyze_message: None")
