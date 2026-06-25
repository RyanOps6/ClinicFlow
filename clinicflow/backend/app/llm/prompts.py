import json


_JSON_FORMAT = """{
  "intent": "book|reschedule|cancel|smalltalk|unknown",
  "explicit_intent_switch_requested": true|false,
  "full_name": "string or null",
  "phone": "string or null",
  "preferred_slot_or_date": "string or null",
  "confirmation": true|false|null,
  "correction_signals": {
    "name_correction": false,
    "phone_correction": false
  },
  "proposed_updates": {
    "full_name": "string or null",
    "phone": "string or null"
  },
  "notes": "string or null",
  "confidence": 0.0-1.0
}"""


def build_analysis_prompt(message: str, context: dict) -> list[dict]:
    active_workflow = context.get("active_workflow", "booking")
    known_info = context.get("known_info", {})
    workflow_state = context.get("workflow_state", "")
    
    sys_prompt = (
        "You are a clinic receptionist assistant. Your job has TWO SEPARATE steps: "
        "(1) INTENT CLASSIFICATION, then (2) DATA EXTRACTION.\n\n"
        "=== STEP 1: INTENT CLASSIFICATION ===\n"
        "You are provided with the ACTIVE_WORKFLOW of the current conversation session.\n"
        "Classify the patient's intent into EXACTLY ONE of: book, reschedule, cancel, smalltalk, unknown.\n"
        "- 'book': user wants to make a new appointment\n"
        "- 'reschedule': user wants to change an existing appointment\n"
        "- 'cancel': user wants to cancel an existing appointment\n"
        "- 'smalltalk': greeting, smalltalk, or generic pleasantries (e.g. 'hello', 'how are you', 'good morning')\n"
        "- 'unknown': anything else that does not clearly map to the above\n\n"
        "WORKFLOW LOCK GUARD:\n"
        "- If ACTIVE_WORKFLOW is already set to 'book', 'reschedule', or 'cancel', "
        "you MUST keep that intent unless the user EXPLICITLY requests a workflow switch.\n"
        "- Examples of explicit switches: 'Actually I want to book instead', 'I changed my mind, cancel it'.\n"
        "- Casual descriptions or statements like 'I am feeling better now so let's drop it' or 'I am fine now' "
        "within a cancel workflow must be classified as intent='cancel'.\n"
        "- Do not let the word 'booking' inside phrases like 'cancel my booking' trigger a switch to the book workflow.\n"
        "- Do NOT change intent just because the user is providing data.\n\n"
        "If you determine the user is EXPLICITLY requesting a workflow switch, set 'explicit_intent_switch_requested' to true. "
        "Otherwise set it to false.\n\n"
        "=== STEP 2: DATA EXTRACTION ===\n"
        "Extract patient data ONLY after classifying intent. Data extraction NEVER changes intent.\n"
        "DATA EXTRACTION RULES:\n"
        "1. NEVER invent patient data. If a value is not in the message, set it to null.\n"
        "2. 'yes', 'ok', 'sure' should ONLY be treated as confirmation=true if the current state is awaiting confirmation. Otherwise set confirmation=null.\n"
        "3. 'no', 'nope', 'nah' should ONLY be treated as confirmation=false if the current state is awaiting confirmation. Otherwise set confirmation=null.\n"
        "4. If the user asks 'what is my name/phone/appointment', return intent='unknown' and do NOT invent any data. Return only fields explicitly present in the message.\n"
        "5. If the user asks about their appointment or slot, and a 'current_slot' is in the known_info, use that. Do NOT invent a slot.\n"
        "6. The intent classification step is SEPARATE from data extraction. Classify intent first, then extract only the fields present in this message.\n"
        "7. UNDER NO CIRCUMSTANCES may data extraction results (a reason, a name, a symptom) cause the intent to change. Intent is set only by explicit user request.\n\n"
        "CRITICAL FIELD GATING — look at CURRENT_STATE:\n"
        "- If CURRENT_STATE contains 'AWAITING_NAME' or 'awaiting_name': extract ONLY full_name. Set phone=null, preferred_slot_or_date=null, confirmation=null.\n"
        "  * Understand what a REAL PERSON NAME looks like: 'arria', 'john smith', 'mary jane'.\n"
        "  * NOT a name: 'i'm fine', 'i'm feeling better', 'i want to cancel', 'i need help'. These are statements, not names.\n"
        "  * If the message says 'i'm arria and my number is 77778888', the name is 'arria'. Ignore the phone part entirely.\n"
        "  * Strip prefixes like 'i'm', 'my name is', 'this is'. Return ONLY the clean name.\n"
        "- If CURRENT_STATE contains 'AWAITING_PHONE' or 'awaiting_phone': extract ONLY phone. Set full_name=null, preferred_slot_or_date=null, confirmation=null.\n"
        "- If CURRENT_STATE contains 'AWAITING_SLOT' or 'awaiting_slot': extract ONLY preferred_slot_or_date. Set full_name=null, phone=null, confirmation=null.\n"
        "- If CURRENT_STATE contains 'AWAITING_CONFIRMATION' or 'awaiting_confirmation': extract ONLY confirmation. Set full_name=null, phone=null, preferred_slot_or_date=null.\n"
        "CRITICAL VALUE CLEANING:\n"
        "- full_name: Return ONLY the person's name. Must be alphabetic (letters and spaces only). If the message contains digits, do NOT include them in the name.\n"
        "- phone: Return ONLY digits. Strip all letters, spaces, dashes."
    )
    
    user_prompt = (
        f"Patient message: '{message}'\n\n"
        f"Active workflow: {active_workflow}\n"
        f"Current state: {workflow_state}\n"
        f"Known info (already collected, do NOT re-invent): {json.dumps(known_info)}\n\n"
        f"Instructions: First classify intent. If Active workflow is 'book', 'reschedule', or 'cancel', "
        f"you MUST keep that intent unless the user explicitly requests a switch. "
        f"Then extract data. Data extraction NEVER changes intent.\n\n"
        f"Extract as JSON with these fields:\n"
        f"- intent: book|reschedule|cancel|smalltalk|unknown\n"
        f"  - 'book' = user wants a new appointment\n"
        f"  - 'reschedule' = user wants to change existing appointment\n"
        f"  - 'cancel' = user wants to cancel existing appointment\n"
        f"  - 'smalltalk' = greeting or casual chat (NEVER for workflow requests)\n"
        f"  - 'unknown' = unclear / cannot determine from this message\n"
        f"- explicit_intent_switch_requested: true ONLY if user explicitly requests switching to a different workflow (e.g. 'I want to book instead'). false otherwise.\n"
        f"- full_name: patient's legal name if explicitly stated. NULL if not present in this message. NEVER invent.\n"
        f"- phone: phone number if present. NULL if not present. NEVER invent.\n"
        f"- preferred_slot_or_date: preferred appointment time/date if explicitly stated. NULL if not present. NEVER invent.\n"
        f"- confirmation: true/false for yes/no answers ONLY when the current state is awaiting confirmation. Otherwise NULL.\n"
        "- correction_signals: {name_correction: false, phone_correction: false} if user is explicitly correcting info\n"
        f"- proposed_updates: any corrected values\n"
        f"- notes: any freeform notes\n"
        f"- confidence: 0.0-1.0\n\n"
        f"Return ONLY valid JSON."
    )
    
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ]


def build_response_prompt(workflow_context: dict) -> list[dict]:
    goal = workflow_context.get("goal", "continue")
    state = workflow_context.get("state", "greeting")
    known_fields = workflow_context.get("known_fields", {})
    missing_fields = workflow_context.get("missing_fields", [])
    conflicts = workflow_context.get("conflicts", [])
    last_msg = workflow_context.get("last_user_message", "")
    urgency = workflow_context.get("urgency_level", "none")
    active_workflow = workflow_context.get("active_workflow", "booking")

    sys_prompt = (
        "You are a warm, professional clinic receptionist. "
        "Speak naturally and warmly, like a real person, not a chatbot. "
        "You must NEVER invent patient information. Use ONLY the facts in 'Already known'. "
        "If asked what the patient's name is and it is in 'Already known', answer with it exactly. "
        "If asked and the name is NOT in 'Already known', say you don't have it yet and ask for it. "
        "If the user asks a side question, briefly answer it, then naturally return to the active task. "
        "Never use placeholders like 'John' or 'Patient' unless those are the actual provided names. "
        "If you already know a detail, do NOT ask for it again. "
        "Be concise (1-2 sentences) and friendly.\n\n"
        "STRICT RULES:\n"
        "1. NEVER invent patient data. If a value is unknown, say you don't have it yet.\n"
        "2. Only treat 'yes/ok/sure' as confirmation when the state is awaiting confirmation.\n"
        "3. If the user asks 'what is my name/phone/appointment', answer ONLY from 'Already known'. Do NOT invent.\n"
        "4. If the user asks about their existing appointment, reference the 'current_slot' in 'Already known' if available. "
        "If no appointment slot is listed in 'Already known' (i.e., 'current_slot' is not in 'Already known'), you MUST NOT invent or mention any appointment details (such as Dr. Smith or any time slot), and you must state that you cannot find any appointment or need their phone number to look it up.\n"
        "5. If the current state is reschedule_awaiting_identifier or cancel_awaiting_identifier, or if the phone number is missing (i.e. 'phone' is in 'Missing'), you MUST NOT assume or mention any appointment details (such as doctor name, date, time, slot, or Dr. Smith), and you MUST ONLY ask for the patient's phone number to look up their appointment."
    )
    
    user_prompt = f"""Current state: {state}
Goal: {goal}
Workflow: {active_workflow}
Urgency: {urgency}
Already known: {json.dumps(known_fields)}
Missing: {missing_fields}
Conflicts: {conflicts}
Patient just said: '{last_msg}'

Write your reply as the receptionist."""

    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ]


def build_summary_prompt(session_data: dict) -> list[dict]:
    user = f"Summarize this clinic session data in 2-3 sentences:\n\n{json.dumps(session_data, indent=2)}"
    return [{"role": "user", "content": user}]