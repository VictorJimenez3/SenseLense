> Provider update: Deepgram Nova-3 is now preferred for transcription when `DEEPGRAM_API_KEY` is set. Groq `openai/gpt-oss-20b` is preferred for summaries when `GROQ_API_KEY` is set. Keys are stored only in ignored local `.env` and Render environment secrets. Gemini/ElevenLabs remain optional legacy paths. Speaker IDs are per audio chunk; seller/client assignment remains a heuristic, not identity verification. Browser audio still uploads in ten-second chunks, so provider speed does not remove that capture delay.

> Current tracker: **face-api.js 0.22.2**, Tiny Face Detector input size 224, hosted with the app under `frontend/assets/face-api/`. No license key, external model CDN or backend face processing is needed. `frontend/js/emotion.js` reads the existing camera video, displays live expression probabilities and inference time, and saves aggregated `faceapi` events every two seconds. It skips missing faces and drains final uploads before saving. Mood and engagement remain explicitly heuristic. MorphCast-specific attention metrics were removed because this model does not supply them. Historical MorphCast/DeepFace events still display. The optional Gemini path remains quota-limited; HTTP 429 now pauses further audio uploads for that session with a clear message.

# SenseLense interview handoff — October 9, 2026

## A. What works / what was fixed

- Browser verified: dashboard totals/navigation, client creation, Sessions search, sample detail, transcript/emotion timeline and synthetic disclosure. A separate Chrome profile entered as Demo Visitor without setup; tutorial Next/Finish controls were exercised. Cloud browser was unavailable. The earlier camera/microphone permission flow was verified. The new face-api.js model was tested in a real browser with a public face fixture, produced happy predictions and timestamped events, and showed 42 ms for a warmed-up inference on this Mac. User tested the official live webcam demo and approved its responsiveness.
- Backend tests cover CRUD, event ingestion, insights, frame errors, transcription mapping, missing credentials, summary deadline and repeatable seed preservation. The live summary failure returned in 44.7 seconds and preserved the saved notes/events. Recorder tests cover chunk offsets, final upload completion and expression shutdown.
- Fixed: destructive random seed, old Settings backend URL, ten-second transcription timestamp shift, summary starting before final audio completes, silent transcription errors, fake neutral samples on DeepFace errors, emotion analysis of frames with no face, and missing summary deadline/404 handling.
- **Unresolved external services:** The legacy Gemini path reports free-tier quota exhaustion. Deepgram and Groq were successfully exercised with a short synthetic test clip and its transcript. Face expression tracking is independent of Gemini. Paid MorphCast is no longer used. These failures are reported; synthetic results are never substituted into a live session.

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

Open http://localhost:8080/. Flask runs on 5050 with local debug reload, so Python edits are picked up during practice. If either port is already occupied, stop your previous app run first; don't start two copies. Ctrl-C stops a new run. The existing Python 3.12 virtualenv is installed. On a fresh checkout: `./setup.sh --seed`, then `./run.sh`.

`backend/.env` is ignored and holds provider keys locally; Render stores them as environment secrets. Deepgram and Groq are the selected providers. No ElevenLabs key is configured. When Gemini is available it handles audio and summaries; adding a valid ElevenLabs key selects its transcription path. Neither is required to review the sample or run browser expression tracking. Changing `.env` requires restarting Flask.

Tests:

```sh
backend/venv/bin/python -m pytest backend/tests -q
node frontend/tests/recording.test.cjs
node frontend/tests/emotion.test.cjs
node frontend/tests/public-demo.test.cjs
node frontend/tests/insights.test.cjs
```

## C. Demo data

Look for **[Demo] Northstar payroll discovery**, client **Alex Morgan [Demo]**. It is a fictional five-minute sales discussion: nine transcript segments, thirty illustrative emotion samples, labelled summary, objection and pilot agreement.

`backend/seed.py` inserts this sample only when absent; it preserves all existing records and can be run repeatedly. Docker runs it on every startup. SQLite lives at `backend/instance/senselense.db` locally and `/app/instance/senselense.db` in Render. Render storage is ephemeral: new recordings can disappear on replacement/redeploy, but the sample is restored automatically. The sample uses the existing event source categories for compatibility; its results were authored as fixtures, not produced by either provider. Don't regenerate its summary during the demo.

## D. Natural demo flow (about five minutes)

1. Dashboard: explain that SenseLense lets a salesperson review what was said alongside estimated facial reactions, rather than taking notes from memory.
2. Clients → Alex Morgan → sample session. Say briefly that this is a clearly labelled synthetic walkthrough dataset.
3. Read the objection at **01:15**, the staged rollout discussion at **02:30**, and pilot agreement at **04:15** in the timeline. Point out timestamp alignment and how the summary supports follow-up.
4. Show emotion breakdown and next steps. Describe scores as heuristics/estimates, not proof of intent.
5. Optionally show New Session: select a client, short title, allow camera/mic, speak for 20–30 seconds, End Session. The expression model is verified with a fixture; live transcript/summary depends on available provider quota. If it is still unavailable tomorrow, demonstrate capture and saved events, then return to the reliable sample. Be candid about the provider failure.
6. When Tim asks about implementation, open `frontend/js/api.js`, then the relevant Flask route. Follow one request rather than touring every file.

## E. Codebase map

| Responsibility | File |
| --- | --- |
| Dashboard and aggregate cards | `frontend/index.html` (inline JavaScript) |
| Clients list/create; client history | `frontend/clients.html`, `frontend/client.html` |
| Session search; timeline/summary rendering | `frontend/sessions.html`, `frontend/session.html` |
| Camera, ten-second audio chunks, saving | `frontend/record.html` (inline JavaScript) |
| HTTP requests / backend URL | `frontend/js/api.js` |
| Browser expression model, live scores and snapshots | `frontend/js/emotion.js` |
| Flask creation, CORS, route registration | `backend/app.py` |
| Clients/sessions/events/insights endpoints | `backend/blueprints/api.py` |
| DeepFace and audio providers | `backend/blueprints/analysis.py` |
| Gemini prompt and summary endpoint | `backend/blueprints/ai.py` |
| SQLAlchemy Client → Session → Event | `backend/models.py` |
| Environment/database configuration; sample | `backend/config.py`, `backend/seed.py` |
| Deployment startup | `backend/Dockerfile` |

Trace: Record button → `api.createSession` → POST `/api/sessions` → SQLAlchemy Session. Camera → `EmotionTracker.start` → face-api.js in the browser → POST `/sessions/<id>/events` → Event rows. Audio → `/transcribe/<id>` → configured provider → Event rows. End → wait for audio and expression uploads → PATCH `/sessions/<id>/end` → POST summary/generate → Gemini → Session.summary. Review → GET session with events + insights → rendered timeline.

This is plain HTML/CSS/JavaScript, Flask and SQLite, not React. No separate relay appears in the current code; recording talks directly to Flask.

## F. Three manual practice changes (not implemented)

1. Add `PATCH /api/clients/<id>` to edit company/notes. Preserve omitted fields; return updated client; check unknown ID and invalid input. Start in `api.py`.
2. Add optional `?client_id=` filtering to GET `/api/sessions`. Preserve the current unfiltered behavior. Add a corresponding argument to `api.getSessions`. Start in `api.py` and `frontend/js/api.js`.
3. Add `duration_ms` to the session response, derived from start/end times; show it in the session detail. Define the result for an active session. Start in `models.py` and `frontend/session.html`.

## G. Remaining risks / honest tradeoffs

- The optional Gemini path is quota exhausted; Deepgram credits and Groq free-tier limits can still be exhausted; provider availability, free-tier limits and the temporary key can affect tomorrow. ElevenLabs path is tested with mocks, not live credentials. Expression-derived scores are heuristics; the replacement does not supply attention estimates.
- Render free tier sleeps with inactivity and has limited CPU/memory. Warm it before demonstrating; avoid redeploying mid-interview. Render deploys are manual; after a backend push use Manual Deploy → Deploy latest commit. GitHub Pages publishes automatically.
- No video/audio playback is stored: only derived timestamped events. Speaker roles are assigned per audio chunk and can swap between chunks. Sentiment/engagement are simple heuristics.
- The visitor/profile identity is localStorage personalization, not backend authentication. Use fictional contacts. Some CRUD input validation and error formatting remain basic.
- No architecture rewrite, persistence service, paid upgrade or practice feature was added.
