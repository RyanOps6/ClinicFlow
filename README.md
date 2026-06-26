# ClinicFlow 🏥

ClinicFlow is an intelligent virtual receptionist and clinic chatbot designed to dynamically manage patient appointments (booking, rescheduling, and cancellation) via natural speech and text interaction. It bridges the gap between structured clinical workflows and fluid human conversations.

---

## 🌟 Key Features

* **Dynamic Conversational Gating**: Acts like a natural receptionist. Gathers patient identity (Name & Phone) dynamically, processes smalltalk, handles intent shifts fluidly, and only initiates a workflow when explicitly requested.
* **Unified Speech & Text WebSocket Streaming**: Real-time bi-directional streaming over active WebSocket channels (`/api/sessions/ws/{session_id}`). Text entries and voice transcriptions are immediately transmitted as binary payloads to allow concurrent text/speech processing.
* **Telemetry & Connection State Indicators**: Interactive green status indicators and active `WebSocket Stream: Connected` badges track socket handshakes automatically on session initialization.
* **Quiet Speech-to-Text Loop**: Seamless background microphone reconnect loops using the Web Speech API without audible beep loops, chime alerts, or recording start/stop tone disruptions.
* **Structured Developer Audit Logs**: Live dashboard-integrated developer log panel showing raw text, pre-turn workflow state, exact LLM prompt payloads, raw JSON outputs from the LLM extractor, and the final action executed by the engine in real time.
* **Simulated Voice Pipeline**: Integrated Speech-to-Text (STT) simulation and offline local Text-to-Speech (TTS) audio synthesis (under `1.0s` response latency) to support future voice/phone integrations.
* **Staff Dashboard & Monitor**: An interactive playground dashboard including a Chat Simulator, Live Session State Monitor, and Appointments Ledger.
* **White-labeled Branding**: Upgraded team cards with classic names (Dr. John Henry, Dr. David Miller) and direct link white-labeled email routing to `contact@clinicflow.ai`.

---

## 🛠️ Technology Stack

### Backend
* **Framework**: FastAPI (Python 3.12+)
* **Database**: SQLite (SQLAlchemy ORM)
* **AI Extraction**: OpenAI GPT & custom grounded prompt context
* **Text-to-Speech (TTS)**: Offline local speech synthesis via Edge-TTS / Edge-TTS communication wrappers
* **Test Suite**: `pytest`

### Frontend
* **Framework**: React (TypeScript)
* **Build Tool**: Vite
* **Styling**: Vanilla CSS & Tailwind CSS
* **Animation**: GSAP (GreenSock Animation Platform)
* **Icons**: Lucide React

---

## 🚀 Getting Started

### Prerequisites
* **Python**: 3.10 or newer installed on your system.
* **Node.js**: 18.x or newer installed on your system.

---

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd clinicflow/backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local configuration file:
   The backend is configured to search for environment files hierarchically. You can place your `.env` file either at the project root (`d:\iclinic\.env`) or inside the backend folder (`d:\iclinic\clinicflow\backend\.env`).
   
   To initialize it from the root:
   ```bash
   # From the repository root:
   cp .env.example .env
   # Open the new .env file and add your OPENAI_API_KEY and OPENAI_BASE_URL
   ```

5. Run the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   The backend API will be available at `http://localhost:8000`.

---

### 2. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd clinicflow/frontend
   ```

2. Install npm packages:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The staff dashboard will be available in your browser at `http://localhost:5173`.

---

## 🧪 Testing & Verification

### Run Backend Unit Tests
To verify all conversation states, gating controls, slot matching, and database models:
```bash
cd clinicflow/backend
pytest -v
```

### Run Live Simulated Voice Test
To verify the end-to-end voice processing loop (Speech -> Extraction Engine -> TTS Audio Generation):
```bash
cd clinicflow/backend
python test_voice_live.py
```
This script runs a test turn, outputs the generated spoken response as a `.wav` file in `clinicflow/backend/voice_replies/`, and prints performance metrics.

### Run LLM API Extraction Test
To verify the LLM extraction client connections and prompt responses without hardcoded keys:
```bash
# From the repository root:
python test_llm3.py
```
```text
Execution Metrics Success!
============================================================
Decoded Speech  : My name is Aryan and I want to cancel my appointment
Bot Text Reply : I'd be help you cancel your appointment. Could you please provide the phone number linked to your appointment?
Audio Output   : D:\iclinic\clinicflow\backend\voice_replies\reply_510_178231419155.wav
============================================================
Latency Performance Telemetry:
   * State Engine Processing : 0.0883s
   * Audio TTS Synthesis     : 0.7774s
   * Total Loop Latency      : 0.8657s
============================================================
```
