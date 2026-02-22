# FILE: api.py - The logic center. This is where you plug in Presage and ElevenLabs data.
import os
import base64
import tempfile
import threading
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, jsonify, request
from models import db, Client, Session, Event
from datetime import datetime

api_bp = Blueprint("api", __name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_abeee70f4b3aea3e51d9f4e375fb196c0ceaf31ae812410d")

# ── DeepFace async executor ───────────────────────────────────────────────────
# All DeepFace work runs in this pool so Flask threads are never blocked.
_df_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="deepface")
_df_ready = False
_df_lock = threading.Lock()

EMOTION_MAP = {
    'happy': 'happy', 'surprise': 'engaged', 'neutral': 'neutral',
    'sad': 'negative', 'disgust': 'negative', 'fear': 'confused', 'angry': 'negative',
}
VALENCE_MAP = {
    'happy': 0.9, 'surprise': 0.3, 'neutral': 0.0,
    'sad': -0.5, 'disgust': -0.7, 'fear': -0.6, 'angry': -0.8,
}


def _warmup_deepface():
    """Pre-load model weights so first real frame is instant."""
    global _df_ready
    try:
        import cv2
        from deepface import DeepFace
        # Tiny 1x1 black image — just enough to trigger model load
        blank = np.zeros((48, 48, 3), dtype=np.uint8)
        DeepFace.analyze(img_path=blank, actions=['emotion'],
                         enforce_detection=False, silent=True,
                         detector_backend='opencv')
        with _df_lock:
            _df_ready = True
        print("[presage] DeepFace model warmed up ✓")
    except Exception as e:
        print(f"[presage] Warmup failed (non-fatal): {e}")


# Kick off warmup in background immediately on import
threading.Thread(target=_warmup_deepface, daemon=True).start()


def _run_deepface(frame_bytes: bytes):
    """Run DeepFace in the thread pool. Returns (emotion, valence, raw)."""
    import cv2
    from deepface import DeepFace
    img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        return None, None, None
    try:
        result = DeepFace.analyze(
            img_path=frame,
            actions=['emotion'],
            enforce_detection=False,
            silent=True,
            detector_backend='opencv',   # <-- MUCH faster than default mtcnn
        )
        if isinstance(result, list):
            result = result[0]
        dominant = result.get('dominant_emotion', 'neutral').lower()
        mapped = EMOTION_MAP.get(dominant, 'neutral')
        valence = VALENCE_MAP.get(dominant, 0.0)
        return mapped, valence, dominant
    except Exception as e:
        print(f"[presage] DeepFace error: {e}")
        return 'neutral', 0.0, 'neutral'


# ── Health ────────────────────────────────────────────────────────────────────

@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "deepface_ready": _df_ready})


# ── Transcribe audio blob from browser ───────────────────────────────────────
# Browser records with MediaRecorder, sends webm/wav blobs here.
# Shorter chunks = faster transcript feedback.

@api_bp.post("/transcribe/<int:session_id>")
def transcribe_chunk(session_id):
    """
    Accepts audio as multipart ('audio' file field).
    Calls ElevenLabs scribe_v2 with diarization, stores events in DB.
    Returns segments immediately.
    """
    Session.query.get_or_404(session_id)

    if 'audio' not in request.files:
        return jsonify({"error": "missing 'audio' file field"}), 400

    audio_file = request.files['audio']
    audio_bytes = audio_file.read()
    fname = audio_file.filename or 'chunk.webm'
    ext = fname.rsplit('.', 1)[-1].lower() or 'webm'

    if len(audio_bytes) < 500:
        return jsonify({"error": f"audio too small ({len(audio_bytes)} bytes)"}), 400

    print(f"[elevenlabs] Received {len(audio_bytes)} bytes of audio ({ext}) for session {session_id}")

    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        # Write to temp file — ElevenLabs SDK needs a seekable file
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, 'rb') as f:
                result = client.speech_to_text.convert(
                    file=f,
                    model_id="scribe_v2",
                    diarize=True,
                )
        finally:
            os.unlink(tmp_path)

        # Log raw result for debugging
        print(f"[elevenlabs] Raw result type: {type(result)}")
        raw_text = getattr(result, 'text', '') or ''
        print(f"[elevenlabs] Full text: {raw_text[:200]}")

        segments = getattr(result, 'segments', None) or []
        if not segments and raw_text.strip():
            # Fallback: no segments but we have text → create one segment
            segments = [type('S', (), {
                'speaker': 'speaker_0', 'text': raw_text, 'start': 0.0, 'end': 0.0
            })()]

        # Get the offset from the frontend (ms since session start)
        offset_base = int(request.args.get("offset_ms", 0))
        seen_labels = []

        def label_to_role(label):
            if label not in seen_labels:
                seen_labels.append(label)
            return 'seller' if seen_labels.index(label) == 0 else 'client'

        events_out = []
        for seg in segments:
            speaker_label = getattr(seg, 'speaker', None) or 'unknown'
            text = (getattr(seg, 'text', '') or '').strip()
            # start is seconds within THIS chunk
            start_ms = int((getattr(seg, 'start', 0) or 0) * 1000)
            if not text:
                continue
            role = label_to_role(speaker_label)
            event = Event(
                session_id=session_id,
                timestamp_ms=offset_base + start_ms,
                source='elevenlabs',
                speaker=role,
                text=text,
            )
            db.session.add(event)
            events_out.append({'speaker': role, 'text': text, 'start_ms': offset_base + start_ms})

        db.session.commit()
        print(f"[elevenlabs] Stored {len(events_out)} segments for session {session_id}")
        return jsonify({"ok": True, "segments": events_out}), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Analyze webcam frame (non-blocking) ──────────────────────────────────────
# Returns 202 immediately; DeepFace runs in background thread pool.
# Result is stored in DB and the next poll by the frontend picks it up.
# For even lower latency, the result is ALSO returned synchronously if the
# thread completes fast enough (timeout=2s).

@api_bp.post("/analyze-frame/<int:session_id>")
def analyze_frame(session_id):
    """
    JSON body: { "frame": "<base64 JPEG data URL>", "timestamp_ms": <int> }
    Returns emotion result synchronously (waits up to 2s for DeepFace).
    Falls back to 'neutral' on timeout so UI never stalls.
    """
    Session.query.get_or_404(session_id)

    data = request.get_json(force=True) or {}
    frame_b64 = data.get('frame', '')
    timestamp_ms = int(data.get('timestamp_ms', 0))

    if not frame_b64:
        return jsonify({"error": "no frame"}), 400

    if ',' in frame_b64:
        frame_b64 = frame_b64.split(',', 1)[1]

    try:
        frame_bytes = base64.b64decode(frame_b64)
    except Exception:
        return jsonify({"error": "bad base64"}), 400

    # Submit to thread pool, wait up to 2s then fall back to neutral
    future = _df_executor.submit(_run_deepface, frame_bytes)
    try:
        mapped, valence, dominant = future.result(timeout=2.0)
    except Exception:
        # Timeout or error — return neutral immediately, don't block UI
        mapped, valence, dominant = 'neutral', 0.0, 'timeout'

    if mapped is None:
        return jsonify({"error": "invalid image"}), 400

    # Store in DB (non-blocking — use a background thread)
    def _store():
        from app import app
        with app.app_context():
            event = Event(
                session_id=session_id,
                timestamp_ms=timestamp_ms,
                source='presage',
                emotion=mapped,
                valence=valence,
            )
            db.session.add(event)
            db.session.commit()

    threading.Thread(target=_store, daemon=True).start()

    return jsonify({"emotion": mapped, "valence": valence, "raw": dominant}), 200


# ── Clients ───────────────────────────────────────────────────────────────────

@api_bp.get("/clients")
def list_clients():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    return jsonify([c.to_dict() for c in clients])


@api_bp.post("/clients")
def create_client():
    data = request.get_json(force=True)
    client = Client(
        name=data.get("name", "Unknown"),
        company=data.get("company", ""),
        email=data.get("email", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


@api_bp.get("/clients/<int:client_id>")
def get_client(client_id):
    client = Client.query.get_or_404(client_id)
    data = client.to_dict()
    data["sessions"] = [s.to_dict() for s in client.sessions]
    return jsonify(data)


# ── Sessions ──────────────────────────────────────────────────────────────────

@api_bp.get("/sessions")
def list_sessions():
    sessions = Session.query.order_by(Session.started_at.desc()).all()
    return jsonify([s.to_dict() for s in sessions])


@api_bp.post("/sessions")
def create_session():
    data = request.get_json(force=True)
    session = Session(
        client_id=data["client_id"],
        title=data.get("title", "Meeting"),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


@api_bp.get("/sessions/<int:session_id>")
def get_session(session_id):
    session = Session.query.get_or_404(session_id)
    include_events = request.args.get("events", "false").lower() == "true"
    return jsonify(session.to_dict(include_events=include_events))


@api_bp.patch("/sessions/<int:session_id>/end")
def end_session(session_id):
    session = Session.query.get_or_404(session_id)
    data = request.get_json(force=True) or {}
    session.ended_at = datetime.utcnow()
    session.summary = data.get("summary", session.summary)
    session.overall_sentiment = data.get("overall_sentiment", session.overall_sentiment)
    session.engagement_score = data.get("engagement_score", session.engagement_score)
    db.session.commit()
    return jsonify(session.to_dict())


# ── Events (Timeline Ingestion) ───────────────────────────────────────────────

@api_bp.post("/sessions/<int:session_id>/events")
def ingest_events(session_id):
    Session.query.get_or_404(session_id)
    items = request.get_json(force=True)
    if not isinstance(items, list):
        items = [items]

    created = []
    for item in items:
        event = Event(
            session_id=session_id,
            timestamp_ms=item.get("timestamp_ms", 0),
            source=item.get("source", "unknown"),
            emotion=item.get("emotion"),
            valence=item.get("valence"),
            speaker=item.get("speaker"),
            text=item.get("text"),
        )
        db.session.add(event)
        created.append(event)

    db.session.commit()
    return jsonify([e.to_dict() for e in created]), 201


# ── Insights ──────────────────────────────────────────────────────────────────

@api_bp.get("/sessions/<int:session_id>/insights")
def get_insights(session_id):
    session = Session.query.get_or_404(session_id)
    events = session.events
    presage_events = [e for e in events if e.source == "presage" and e.valence is not None]
    elevenlabs_events = [e for e in events if e.source == "elevenlabs"]

    avg_valence = (
        sum(e.valence for e in presage_events) / len(presage_events)
        if presage_events else 0.0
    )

    emotion_counts = {}
    for e in presage_events:
        if e.emotion:
            emotion_counts[e.emotion] = emotion_counts.get(e.emotion, 0) + 1

    return jsonify({
        "session_id": session_id,
        "summary": session.summary,
        "overall_sentiment": session.overall_sentiment,
        "engagement_score": session.engagement_score,
        "avg_valence": round(avg_valence, 3),
        "emotion_breakdown": emotion_counts,
        "transcript_chunks": len(elevenlabs_events),
        "presage_samples": len(presage_events),
    })
