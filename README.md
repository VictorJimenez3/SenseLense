# SenseLense

SenseLense is a sales-call dashboard combining DeepFace facial emotion analysis,
in-browser MorphCast analytics, ElevenLabs transcription, and Gemini summaries.
Flask stores clients, sessions, transcript segments, and emotion events in SQLite.

## Prerequisites

- Python 3.10–3.12 (TensorFlow does not support Python 3.13 yet).
- [uv](https://docs.astral.sh/uv/) is recommended; setup also supports pip.

## Setup

From the repository root:

```bash
bash setup.sh
```

Add `--seed` to also load sample clients, sessions, and events:

```bash
bash setup.sh --seed
```

## API keys

Setup copies `backend/.env.example` to `backend/.env` if needed. Add your keys:

- `ELEVENLABS_API_KEY`: [ElevenLabs API Keys](https://elevenlabs.io/app/settings/api-keys)
- `GEMINI_API_KEY`: [Google AI Studio](https://aistudio.google.com/apikey)
- `GEMINI_MODEL` defaults to `gemini-2.5-flash`; `SECRET_KEY` is used by Flask.

## Run

From the repository root, start both local servers:

```bash
bash run.sh
```

Or run them in separate terminals:

```bash
# Terminal 1
cd backend && source venv/bin/activate && flask run
# Terminal 2
cd frontend && python3 -m http.server 8080
```

Open <http://localhost:8080/login.html>. **Do not open HTML files via
`file://`**: `frontend/js/api.js` uses the production API URL unless the
hostname is `localhost` or `127.0.0.1`.

### Tests

```bash
cd backend
uv pip install --python venv/bin/python -r requirements-dev.txt
venv/bin/pytest
```

## Project structure

```text
SenseLense/
├── backend/
│   ├── .env.example
│   ├── .dockerignore
│   ├── .flaskenv
│   ├── Dockerfile
│   ├── app.py, config.py, models.py, seed.py
│   ├── requirements.txt, requirements-dev.txt, pytest.ini
│   ├── tests/{conftest.py, test_api.py}
│   └── blueprints/{ai.py, analysis.py, api.py}
├── frontend/
│   ├── login.html, index.html, clients.html, client.html
│   ├── sessions.html, session.html, record.html, settings.html
│   ├── assets/adp-logo.svg
│   ├── css/styles.css
│   └── js/{api.js, auth.js, morphcast.js, theme.js, tutorial.js, utils.js}
├── .github/workflows/pages.yml
├── deploy/hf_space.sh
├── run.sh
└── setup.sh
```

## Data pipeline

```text
Browser (record.html)
  ├── every 2.4s: JPEG → POST /api/analyze-frame/<id> → DeepFace → SQLite
  ├── every 10s: WebM → POST /api/transcribe/<id> → ElevenLabs scribe_v2 → SQLite
  └── every 20s: MorphCast → POST /api/sessions/<id>/events → SQLite

End → PATCH /api/sessions/<id>/end
     → POST /api/sessions/<id>/summary/generate → Gemini
```

Transcription: ElevenLabs returns words with speaker ids; consecutive words
from one speaker are merged into a segment; first speaker in a chunk = seller.

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Backend status and DeepFace readiness |
| `GET` / `POST` | `/api/clients` | List or create clients |
| `GET` | `/api/clients/<id>` | Get a client and its sessions |
| `GET` / `POST` | `/api/sessions` | List or create sessions |
| `GET` | `/api/sessions/<id>?events=true` | Get a session and its events |
| `PATCH` | `/api/sessions/<id>/end` | End a session and update metrics |
| `DELETE` | `/api/sessions/<id>` | Delete a session |
| `POST` | `/api/sessions/<id>/events` | Store emotion or transcript events |
| `POST` | `/api/transcribe/<id>` | Transcribe audio with ElevenLabs |
| `POST` | `/api/analyze-frame/<id>` | Analyze a JPEG frame with DeepFace |
| `GET` | `/api/sessions/<id>/insights` | Get session emotion and transcript metrics |
| `POST` | `/api/sessions/<id>/summary/generate` | Generate a summary with Gemini |

## Deploy

- Backend demo deployment: `https://senselense-backend.vercel.app`. It runs the
  Flask API as a Vercel Python function with writable temporary SQLite storage;
  data is not durable across cold starts. The DeepFace/TensorFlow worker is not
  bundled in this lightweight deployment. Audio transcription uses Gemini when
  `ELEVENLABS_API_KEY` is absent, so set `GEMINI_API_KEY` in Vercel's Production
  environment for the interview demo. Use the Hugging Face Docker Space path
  below when DeepFace frame analysis and durable storage are required.
- Backend: run `bash deploy/hf_space.sh <user>`, then add the
  `ELEVENLABS_API_KEY` and `GEMINI_API_KEY` Space secrets. Render was dropped
  because TensorFlow needs more than 512 MB.
- Frontend: push to `main` for GitHub Pages; set the Pages source to
  **GitHub Actions**.
- After the Space is up, set `DEFAULT_BASE` in `frontend/js/api.js` to
  `https://<user>-senselense-backend.hf.space`.

## Troubleshooting

- **Backend offline:** check Flask on port 5050 and
  `http://localhost:5050/api/health`.
- **Camera or mic:** grant browser permissions and use a browser with
  camera and `MediaRecorder` support.
- **First DeepFace frame is slow:** initial TensorFlow/model loading takes time.
- **Transcription returns 503:** both `ELEVENLABS_API_KEY` and `GEMINI_API_KEY`
  are missing from the backend environment.
- **App uses the wrong backend:** the Settings URL override is saved in browser
  localStorage; clear it in Settings to restore automatic detection.
