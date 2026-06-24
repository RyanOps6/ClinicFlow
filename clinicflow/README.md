# ClinicFlow AI

A call-first clinic voice workflow backend + staff dashboard. MVP for a healthcare voice-agent workflow demo.

## Quickstart

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # edit OPENAI_API_KEY if desired (optional)
python -m uvicorn app.main:app --reload --port 8000
```

API runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. API proxy configured to `localhost:8000`.

## Architecture

See `docs/architecture.md` for full details.

### High-Level

- **Backend**: FastAPI + SQLAlchemy + SQLite. State-machine-driven conversation workflow.
- **Frontend**: React + Vite + TypeScript. 4 pages: Dashboard, Session (call simulator), Appointments, Session Detail.
- **AI Layer**: Optional OpenAI integration for improved extraction, response generation, and summaries. Falls back to deterministic rules when no API key is configured.

### Slice 1 (Implemented)

Booking workflow end-to-end:
1. Start simulated session
2. Collect patient name, phone, reason
3. Show available slots
4. Confirm and create appointment in DB
5. View result in SessionPage

## Project Structure

```
clinicflow/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI app, CORS, lifespan
│  │  ├─ core/                 # config, db, constants
│  │  ├─ models/               # Patient, Appointment, CallSession, EventLog
│  │  ├─ schemas/              # Pydantic request/response models
│  │  ├─ api/routes/           # health, sessions, appointments, dashboard, intake, webhooks
│  │  ├─ services/             # conversation, appointment, availability, triage, summary, ai_assistant, etc.
│  │  ├─ llm/                  # OpenAI client + prompt templates (optional)
│  │  └─ utils/                # text helpers, slot utils
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ api/client.ts         # fetch wrapper
│  │  ├─ pages/                # 4 pages
│  │  ├─ components/           # 6 components
│  │  └─ types/index.ts        # TypeScript interfaces
│  ├─ package.json
│  └─ vite.config.ts
├─ README.md
└─ docs/architecture.md
```

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| POST | `/api/sessions/start` | Start a new call session |
| POST | `/api/sessions/{id}/message` | Send patient message (core booking flow) |
| GET | `/api/sessions/{id}` | Get session snapshot |
| GET | `/api/appointments` | List appointments |
| POST | `/api/appointments/{id}/reschedule` | Reschedule appointment |
| POST | `/api/appointments/{id}/cancel` | Cancel appointment |
| GET | `/api/dashboard/overview` | Dashboard stats |
| POST | `/api/webhooks/voice` | Simulated webhook receiver |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./clinicflow.db` | Database URL |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for AI-assisted extraction |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |

When `OPENAI_API_KEY` is empty, the system runs fully deterministically.

## Triage

Rule-based urgency detection. Triggers on keywords like "chest pain", "trouble breathing", "severe bleeding", "fainting", "stroke symptoms". No AI involvement in medical decisions.

## Current MVP Scope

- Booking flow: complete (Slice 1)
- Reschedule/cancel: routes exist, UI scaffolded
- Intake: route scaffolded
- Webhook: endpoint scaffolded
- AI integration: architecture in place, requires API key
- Authentication: not implemented
- Telephony: not implemented (simulated only)

## Future Integration Points

See `docs/architecture.md` for Twilio/Retell integration design.
