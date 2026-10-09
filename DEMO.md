# SenseLense interview handoff — October 9, 2026

## A. What works / what was fixed

- Browser verified: dashboard totals/navigation, client creation, Sessions search, sample detail, transcript/emotion timeline and synthetic disclosure. Live camera + microphone permission flow creates and ends a session; Render stored actual DeepFace camera samples.
- Backend tests cover CRUD, event ingestion, insights, frame errors, transcription mapping, missing credentials, summary deadline and repeatable seed preservation. Recorder tests cover chunk offsets, final upload completion and MorphCast shutdown.
- Fixed: destructive random seed, old Settings backend URL, ten-second transcription timestamp shift, summary starting before final audio completes, silent transcription errors, fake neutral samples on DeepFace errors, and missing summary deadline/404 handling.
- **Unresolved external services:** Gemini generation/transcription timed out tonight through Render and directly. A successful live transcript/summary is NOT verified. MorphCast rejects the existing license. DeepFace works independently. These failures are reported; synthetic results are never substituted into a live session.

## B. Run it

Hosted app: https://victorjimenez3.github.io/SenseLense/

Fresh visitors enter automatically as Demo Visitor; Tim needs no account or credentials. The profile screen is optional personalization.

Open it five minutes before the interview. Check https://senselense-deepface.onrender.com/api/health until `deepface_ready` is true. Settings → Backend URL should be blank (automatic Render default) or `https://senselense-deepface.onrender.com`. Hard refresh if old scripts are cached.

Local, from this existing checkout:

```sh
cd /Users/victor/SenseLense
(cd backend && venv/bin/python seed.py)
./run.sh
```

Open http://localhost:8080/login.html. Flask runs on 5050. If either port is already occupied, stop your previous app run first; don't start two copies. Ctrl-C stops a new run. The existing Python 3.12 virtualenv is installed. On a fresh checkout: `./setup.sh --seed`, then `./run.sh`.

`backend/.env` is ignored and contains the provided temporary Gemini key locally; Render has it as an environment secret. No ElevenLabs key is configured. When Gemini is available it handles audio and summaries; adding a valid ElevenLabs key selects its transcription path. Neither is required to review the sample or run DeepFace. Changing `.env` requires restarting Flask.

Tests:

```sh
backend/venv/bin/python -m pytest backend/tests -q
node frontend/tests/recording.test.cjs
node frontend/tests/morphcast.test.cjs
node frontend/tests/public-demo.test.cjs
```

## C. Demo data

Look for **[Demo] Northstar payroll discovery**, client **Alex Morgan [Demo]**. It is a fictional five-minute sales discussion: nine transcript segments, thirty illustrative emotion samples, labelled summary, objection and pilot agreement.

`backend/seed.py` inserts this sample only when absent; it preserves all existing records and can be run repeatedly. Docker runs it on every startup. SQLite lives at `backend/instance/senselense.db` locally and `/app/instance/senselense.db` in Render. Render storage is ephemeral: new recordings can disappear on replacement/redeploy, but the sample is restored automatically. The sample uses the existing event source categories for compatibility; its results were authored as fixtures, not produced by either provider. Don't regenerate its summary during the demo.

## D. Natural demo flow (about five minutes)

1. Dashboard: explain that SenseLense lets a salesperson review what was said alongside estimated facial reactions, rather than taking notes from memory.
2. Clients → Alex Morgan → sample session. Say briefly that this is a clearly labelled synthetic walkthrough dataset.
3. Read the objection at **01:15**, the staged rollout discussion at **02:30**, and pilot agreement at **04:15** in the timeline. Point out timestamp alignment and how the summary supports follow-up.
4. Show emotion breakdown and next steps. Describe scores as heuristics/estimates, not proof of intent.
5. Optionally show New Session: select a client, short title, allow camera/mic, speak for 20–30 seconds, End Session. Camera analysis is verified; live transcript/summary depends on Gemini recovering. If it is still unavailable tomorrow, demonstrate capture and saved events, then return to the reliable sample. Be candid about the provider failure.
6. When Tim asks about implementation, open `frontend/js/api.js`, then the relevant Flask route. Follow one request rather than touring every file.

## E. Codebase map

| Responsibility | File |
| --- | --- |
| Dashboard and aggregate cards | `frontend/index.html` (inline JavaScript) |
| Clients list/create; client history | `frontend/clients.html`, `frontend/client.html` |
| Session search; timeline/summary rendering | `frontend/sessions.html`, `frontend/session.html` |
| Camera, ten-second audio chunks, saving | `frontend/record.html` (inline JavaScript) |
| HTTP requests / backend URL | `frontend/js/api.js` |
| Optional browser facial SDK | `frontend/js/morphcast.js` |
| Flask creation, CORS, route registration | `backend/app.py` |
| Clients/sessions/events/insights endpoints | `backend/blueprints/api.py` |
| DeepFace and audio providers | `backend/blueprints/analysis.py` |
| Gemini prompt and summary endpoint | `backend/blueprints/ai.py` |
| SQLAlchemy Client → Session → Event | `backend/models.py` |
| Environment/database configuration; sample | `backend/config.py`, `backend/seed.py` |
| Deployment startup | `backend/Dockerfile` |

Trace: Record button → `api.createSession` → POST `/api/sessions` → SQLAlchemy Session. Camera/audio → `/analyze-frame/<id>` or `/transcribe/<id>` → provider → Event rows. End → wait for audio uploads → PATCH `/sessions/<id>/end` → POST summary/generate → Gemini → Session.summary. Review → GET session with events + insights → rendered timeline.

This is plain HTML/CSS/JavaScript, Flask and SQLite, not React. No separate relay appears in the current code; recording talks directly to Flask.

## F. Three manual practice changes (not implemented)

1. Add `PATCH /api/clients/<id>` to edit company/notes. Preserve omitted fields; return updated client; check unknown ID and invalid input. Start in `api.py`.
2. Add optional `?client_id=` filtering to GET `/api/sessions`. Preserve the current unfiltered behavior. Add a corresponding argument to `api.getSessions`. Start in `api.py` and `frontend/js/api.js`.
3. Add `duration_ms` to the session response, derived from start/end times; show it in the session detail. Define the result for an active session. Start in `models.py` and `frontend/session.html`.

## G. Remaining risks / honest tradeoffs

- Gemini is configured but currently timing out; provider availability, free-tier limits and the temporary key can affect tomorrow. ElevenLabs path is tested with mocks, not live credentials. MorphCast attention/valence panels require a renewed license and are not verified live.
- Render free tier sleeps with inactivity and has limited CPU/memory. Warm it before demonstrating; avoid redeploying mid-interview. Render deploys are manual; after a backend push use Manual Deploy → Deploy latest commit. GitHub Pages publishes automatically.
- No video/audio playback is stored: only derived timestamped events. Speaker roles are assigned per audio chunk and can swap between chunks. Sentiment/engagement are simple heuristics.
- Sign-in is a localStorage demo identity, not backend authentication. Use fictional contacts. Some CRUD input validation and error formatting remain basic.
- No architecture rewrite, persistence service, paid upgrade or practice feature was added.
