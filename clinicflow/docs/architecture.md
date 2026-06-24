# ClinicFlow AI — Architecture

## System Design

```
┌────────────────────────────────────────────────┐
│                   Frontend                      │
│         React + Vite + TypeScript              │
│  Dashboard │ Session │ Appointments │ Detail   │
└──────────────────────┬─────────────────────────┘
                       │ HTTP / JSON
                       ▼
┌────────────────────────────────────────────────┐
│              FastAPI Backend                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Routes   │  │ Services  │  │  SQLAlchemy   │  │
│  │          │─▶│          │─▶│  Models       │  │
│  └──────────┘  └──────────┘  └──────┬───────┘  │
│       │                             │          │
│       ▼                             ▼          │
│  ┌──────────┐                 ┌──────────┐     │
│  │  LLM     │ (optional)      │  SQLite   │     │
│  │  Client  │                 │  (file)   │     │
│  └──────────┘                 └──────────┘     │
└────────────────────────────────────────────────┘
```

## Data Flow (Booking)

```
1. Start Session → POST /api/sessions/start
   └─ Creates CallSession (status=active, state=greeting)
   └─ Returns greeting message

2. Send Message → POST /api/sessions/{id}/message
   └─ Append message to transcript
   └─ Optional AI extraction (if key configured) → ExtractionResult
   └─ Deterministic fallback extraction → ExtractionResult
   └─ Merge extracted fields into collected_data
   └─ Rule-based triage on symptoms/reason text
   └─ State machine determines next step:
        greeting → awaiting_name → awaiting_phone →
        awaiting_reason → awaiting_slot_selection →
        awaiting_confirmation → completed
   └─ When completed: create Patient + Appointment in DB
   └─ Optional AI response generation (if key configured)
   └─ Deterministic fallback response
   └─ Log events, save session
   └─ Return assistant message + session snapshot
```

## Services

| Service | Responsibility | AI-Assisted |
|---------|---------------|-------------|
| `conversation_service.py` | Authoritative state machine. Owns workflow logic, state transitions, booking creation. | Calls ai_assistant_service |
| `ai_assistant_service.py` | Centralized AI layer. analyze_message, generate_response, generate_summary. Returns None on failure. | Yes (via llm client) |
| `session_store.py` | CRUD for CallSession: get, create, append transcript, update collected data | No |
| `appointment_service.py` | CRUD for Appointment + find_or_create_patient | No |
| `availability_service.py` | Generates fake hourly slots (9AM-5PM, next 7 days) | No |
| `triage_service.py` | Keyword-based urgency detection. No AI. | No |
| `summary_service.py` | Structured staff-facing summary. AI or template. | Via ai_assistant_service |
| `event_service.py` | Writes EventLog rows | No |
| `intake_service.py` | Intake step tracking | No (scaffolded) |

## State Machine (Booking)

```
GREETING
   │  User: "I want to book" (no clear name)
   ▼
AWAITING_NAME
   │  User: "My name is Priya Sharma"
   ▼
AWAITING_PHONE
   │  User: "555-123-4567"
   ▼
AWAITING_REASON
   │  User: "I have a persistent cough"
   ▼
AWAITING_SLOT_SELECTION
   │  System: shows available slots
   │  User: "Tuesday at 2pm"
   ▼
AWAITING_CONFIRMATION
   │  User: "Yes"
   ▼
COMPLETED → creates Patient + Appointment
```

All state transitions are deterministic. AI only assists with extraction quality and response naturalness.

## Hybrid AI Model

```
Patient Message
     │
     ├─ AI Extraction ── success ──▶ Merge into collected_data
     │  (if key configured)         (fields not extracted
     │    │ fail / no key            fall through to next step)
     │    ▼
     └─ Deterministic Extraction ──▶ Merge into collected_data
     
     ▼
Triage (rule-based only)
     ▼
State Machine (deterministic)
     ▼
Response Generation
     ├─ AI (natural phrasing) ── success ──▶ Return
     │  (if key configured)    fail/no key
     │    ▼
     └─ Template ──────────────────────────▶ Return
```

## Route Table

| Method | Route | Handler | Status |
|--------|-------|---------|--------|
| GET | `/health` | `health.py` | ✅ |
| POST | `/api/sessions/start` | `sessions.py` | ✅ |
| POST | `/api/sessions/{id}/message` | `sessions.py` | ✅ Core booking |
| GET | `/api/sessions/{id}` | `sessions.py` | ✅ |
| GET | `/api/appointments` | `appointments.py` | ✅ |
| POST | `/api/appointments/{id}/reschedule` | `appointments.py` | ✅ Route exists |
| POST | `/api/appointments/{id}/cancel` | `appointments.py` | ✅ Route exists |
| GET | `/api/dashboard/overview` | `dashboard.py` | ✅ |
| POST | `/api/intake/submit` | `intake.py` | 🚧 Scaffolded |
| POST | `/api/webhooks/voice` | `webhooks.py` | 🚧 Scaffolded |

## Future Integration: Twilio / Retell

The webhook endpoint at `/api/webhooks/voice` is designed to receive call events from:
- **Twilio**: Voice webhooks for incoming/outgoing calls, speech-to-text, TwiML instructions
- **Retell AI**: Agent webhooks for call events, transcripts, end-of-call reports

Integration plan:
1. Replace simulated channel with `twilio` or `retell` in CallSession.channel
2. Webhook handler parses provider-specific payload into standard event format
3. `conversation_service.py` is provider-agnostic — it consumes and produces messages regardless of channel
4. Async webhook responses return assistant messages as TwiML or Retell agent replies

## Database Schema

```
Patient
  id (PK), full_name, phone, dob_or_age_group?, insurance_provider?,
  created_at, updated_at

Appointment
  id (PK), patient_id (FK→Patient), appointment_type,
  doctor_name?, scheduled_date, scheduled_time, status,
  reason_for_visit, notes?, created_at, updated_at

CallSession
  id (PK), patient_id (FK→Patient)?, session_type, channel,
  status, intent, workflow_state?, collected_data_json,
  transcript_json, offered_slots_json?, selected_slot?,
  summary_text?, urgency_level, started_at, ended_at?,
  created_at, updated_at

EventLog
  id (PK), session_id (FK→CallSession), event_type,
  payload_json?, created_at
```
