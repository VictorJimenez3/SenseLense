# SenseLense 🎯

> Real-time sales conversation intelligence for ADP — powered by ElevenLabs (transcription) and DeepFace (emotion detection).

---

## What it does

SenseLense listens to a sales call through your browser's microphone and webcam, then in real-time:
- **Transcribes** the conversation with speaker diarization (seller vs client) via ElevenLabs
- **Detects emotions** from the client's face every 2.4 seconds via DeepFace
- **Stores everything** in a local SQLite database with millisecond timestamps
- **Displays** a live dashboard with emotion chips, valence bars, and a growing transcript

---

## Setup (teammates — start here)

### Prerequisites
- **Python 3.9+** — check with `python3 --version`
- **Git** — to clone the repo

### One-command setup

```bash
git clone https://github.com/VictorJimenez3/SenseLense.git
cd SenseLense

# Run the setup script — creates venv, installs all deps, inits DB
bash setup.sh
```

That's it. The script will:
1. Create a Python virtual environment in `backend/venv/`
2. Install all dependencies (Flask, ElevenLabs, DeepFace, TensorFlow, OpenCV…)
3. Create a `backend/Transcriptions/.env` template if one doesn't exist
4. Initialize the SQLite database

> ⚠️ **First run takes ~3-5 minutes** — TensorFlow + DeepFace are large downloads.

---

### Add your API keys

Edit `backend/Transcriptions/.env`:

```env
ELEVENLABS_API_KEY=your_key_here
PRESAGE_API_KEY=your_key_here
```

Get your ElevenLabs key at [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)

> Keys are already set in `.env` if you're working from Eren's machine.

---

### Run the app

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
flask run
# → Running on http://127.0.0.1:5050
```

**Browser:**
```bash
open frontend/login.html
# or just double-click the file in Finder
```

---

## Project structure

```
SenseLense/
├── backend/
│   ├── app.py                  # Flask app factory + /api/record endpoint
│   ├── models.py               # SQLAlchemy models (Client, Session, Event)
│   ├── config.py               # Configuration (DB URI, secret key)
│   ├── requirements.txt        # All Python dependencies
│   ├── .flaskenv               # Flask environment (port 5050, threading on)
│   ├── blueprints/
│   │   └── api.py              # All REST endpoints
│   ├── Transcriptions/
│   │   ├── main.py             # Standalone ElevenLabs recording script
│   │   └── .env                # API keys (git-ignored)
│   ├── database/
│   │   ├── schema.sql          # Raw SQL schema (for reference)
│   │   └── db_manager.py       # Low-level SQLite helpers
│   └── presage_capture.py      # Standalone webcam emotion capture
├── frontend/
│   ├── login.html              # Entry point — open this in browser
│   ├── index.html              # Dashboard
│   ├── clients.html            # Client list + Add Client
│   ├── client.html             # Individual client profile
│   ├── sessions.html           # Session history
│   ├── record.html             # Live recording session
│   ├── session.html            # Session detail / transcript viewer
│   ├── settings.html           # App settings
│   ├── css/styles.css          # Full design system
│   └── js/
│       ├── api.js              # Flask API client (window.api)
│       ├── utils.js            # Shared utilities (window.utils)
│       └── auth.js             # Local session management
├── setup.sh                    # ← Run this first
└── README.md
```

---

## How the real-time pipeline works

```
Browser (record.html)
  │
  ├── every 2.4s → canvas JPEG → POST /api/analyze-frame/<session_id>
  │                                   └─ DeepFace (opencv, pre-warmed)
  │                                       └─ emotion + valence → DB → UI chips update
  │
  └── every 10s  → WebM audio → POST /api/transcribe/<session_id>
                                     └─ ElevenLabs scribe_v2 (diarized)
                                         └─ text segments → DB → transcript feed
```

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend status + DeepFace ready flag |
| `GET` | `/api/clients` | List all clients |
| `POST` | `/api/clients` | Create a client |
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create a session |
| `PATCH` | `/api/sessions/<id>/end` | End a session |
| `GET` | `/api/sessions/<id>?events=true` | Get session + events |
| `POST` | `/api/transcribe/<session_id>` | Receive audio → ElevenLabs |
| `POST` | `/api/analyze-frame/<session_id>` | Receive JPEG → DeepFace |
| `POST` | `/api/record` | Trigger background transcription |
| `GET` | `/api/sessions/<id>/insights` | Emotion + transcript summary |

---

## Troubleshooting

**Backend offline (red dot in sidebar)**
```bash
cd backend && source venv/bin/activate && flask run
```

**`ModuleNotFoundError`**
```bash
cd backend && source venv/bin/activate && pip install -r requirements.txt
```

**Camera/mic not working**
- Allow camera + microphone when the browser asks
- Use Chrome or Edge (Safari has MediaRecorder limitations)

**First emotion detection is slow**
- Normal — DeepFace loads the TensorFlow model on startup (~10s)
- Subsequent frames are fast (opencv detector, thread pool)
