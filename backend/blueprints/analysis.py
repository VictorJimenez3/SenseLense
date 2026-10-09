"""ML endpoints: DeepFace emotion on webcam frames, ElevenLabs transcription on audio chunks."""
import base64
import json
import tempfile
import threading
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from elevenlabs.client import ElevenLabs
from flask import Blueprint, current_app, jsonify, request

from models import db, Event, Session
from werkzeug.exceptions import TooManyRequests

analysis_bp = Blueprint("analysis", __name__)

_df_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="deepface")
_df_ready = False
_df_lock = threading.Lock()

EMOTION_MAP = {
    "happy": "happy",
    "surprise": "engaged",
    "neutral": "neutral",
    "sad": "negative",
    "disgust": "negative",
    "fear": "confused",
    "angry": "negative",
}
VALENCE_MAP = {
    "happy": 0.9,
    "surprise": 0.3,
    "neutral": 0.0,
    "sad": -0.5,
    "disgust": -0.7,
    "fear": -0.6,
    "angry": -0.8,
}


def _warmup_deepface():
    """Load DeepFace's emotion model."""
    global _df_ready
    try:
        import cv2
        from deepface import DeepFace

        blank = np.zeros((48, 48, 3), dtype=np.uint8)
        DeepFace.analyze(
            img_path=blank,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
            detector_backend="opencv",
        )
        with _df_lock:
            _df_ready = True
        print("[deepface] DeepFace model warmed up ✓")
    except Exception as e:
        print(f"[deepface] Warmup failed (non-fatal): {e}")


# Load the TensorFlow model once at startup so the first real frame is fast.
threading.Thread(target=_warmup_deepface, daemon=True).start()


def deepface_ready():
    return _df_ready


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
            enforce_detection=True,
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
        if isinstance(e, ValueError) and "Face could not be detected" in str(e):
            return None, None, "no_face"
        print(f"[deepface] DeepFace error: {e}")
        raise RuntimeError("DeepFace analysis unavailable") from e


@analysis_bp.post("/analyze-frame/<int:session_id>")
def analyze_frame(session_id):
    """Body: {"frame": "data:image/jpeg;base64,...", "timestamp_ms": int}. Returns the detected emotion."""
    Session.query.get_or_404(session_id)
    data = request.get_json(force=True) or {}
    frame_b64 = data.get("frame", "")
    if not frame_b64:
        return jsonify({"error": "no frame"}), 400
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    try:
        frame_bytes = base64.b64decode(frame_b64, validate=True)
    except Exception:
        return jsonify({"error": "bad base64"}), 400

    # Keep requests bounded; unavailable analysis must not become a fake neutral sample.
    future = _df_executor.submit(_run_deepface, frame_bytes)
    try:
        emotion, valence, raw = future.result(timeout=2.0)
    except Exception:
        future.cancel()
        return jsonify({"error": "DeepFace is busy or unavailable; try the next frame"}), 503
    if raw == "no_face":
        return jsonify({"error": "No face detected; frame skipped"}), 422
    if emotion is None:
        return jsonify({"error": "invalid image"}), 400

    db.session.add(
        Event(
            session_id=session_id,
            timestamp_ms=int(data.get("timestamp_ms", 0)),
            source="deepface",
            emotion=emotion,
            valence=valence,
        )
    )
    db.session.commit()
    return jsonify({"emotion": emotion, "valence": valence, "raw": raw})


def _group_words_by_speaker(words):
    """ElevenLabs returns individual words with a speaker_id. Merge consecutive words from the
    same speaker into one segment: {"speaker", "text", "start"} (start in seconds)."""
    segments = []
    for word in words:
        if word.type == "audio_event":
            continue
        speaker = word.speaker_id or "speaker_0"
        if segments and segments[-1]["speaker"] == speaker:
            segments[-1]["text"] += word.text
        else:
            segments.append(
                {"speaker": speaker, "text": word.text, "start": word.start or 0.0}
            )
    return segments


def _transcribe_with_gemini(audio_bytes: bytes, mime_type: str, api_key: str):
    """Use Gemini audio understanding as a no-ElevenLabs transcription fallback.

    The browser sends short WebM chunks, which stay below Gemini's inline request
    limit. Return the same small segment shape used by the ElevenLabs path.
    """
    model = (
        current_app.config.get("GEMINI_TRANSCRIBE_MODEL")
        or current_app.config.get("GEMINI_MODEL")
        or "gemini-3.7-flash"
    )
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": (
                        "Transcribe this audio chunk. Return JSON only in this exact shape: "
                        '{"segments":[{"speaker":"speaker_0","text":"...",'
                        '"start_seconds":0.0}]}. Preserve the spoken words, assign stable '
                        "speaker_0/speaker_1 labels within this chunk, and use 0 for a missing start time."
                    )
                },
                {
                    "inline_data": {
                        "mime_type": mime_type or "audio/webm",
                        "data": base64.b64encode(audio_bytes).decode("ascii"),
                    }
                },
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise TooManyRequests(description="Gemini quota exhausted. Transcription is unavailable until quota resets or another provider is configured.") from exc
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini transcription failed ({exc.code}): {detail[:500]}") from exc

    text = "".join(
        part.get("text", "")
        for part in result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    ).strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    parsed = json.loads(text)
    segments = []
    for segment in parsed.get("segments", []):
        clean_text = str(segment.get("text", "")).strip()
        if clean_text:
            segments.append({
                "speaker": str(segment.get("speaker", "speaker_0")),
                "text": clean_text,
                "start": float(segment.get("start_seconds", 0.0) or 0.0),
            })
    return segments


@analysis_bp.post("/transcribe/<int:session_id>")
def transcribe_chunk(session_id):
    """Multipart field 'audio' (10s webm from the browser). ?offset_ms= is where this chunk starts
    in the session, so word timestamps can be placed on the session timeline."""
    Session.query.get_or_404(session_id)
    api_key = current_app.config["ELEVENLABS_API_KEY"]
    gemini_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key and not gemini_key:
        return jsonify({"error": "Set ELEVENLABS_API_KEY or GEMINI_API_KEY"}), 503
    if "audio" not in request.files:
        return jsonify({"error": "missing 'audio' file field"}), 400
    audio_bytes = request.files["audio"].read()
    if len(audio_bytes) < 500:
        return jsonify({"error": f"audio too small ({len(audio_bytes)} bytes)"}), 400
    offset_ms = int(request.args.get("offset_ms", 0))

    # Gemini can handle short WebM audio inline, so the demo remains usable when
    # an ElevenLabs key is unavailable. Keep the event source name stable for the
    # existing insights and summary queries.
    if not api_key:
        try:
            segments = _transcribe_with_gemini(
                audio_bytes,
                request.files["audio"].mimetype or "audio/webm",
                gemini_key,
            )
        except TooManyRequests as exc:
            return jsonify({"error": exc.description, "code": "quota_exhausted"}), 429
        except Exception as exc:
            traceback.print_exc()
            return jsonify({"error": str(exc)}), 502

        roles = {}
        events = []
        for segment in segments:
            role = roles.setdefault(
                segment["speaker"], "seller" if not roles else "client"
            )
            event = Event(
                session_id=session_id,
                timestamp_ms=offset_ms + int(segment["start"] * 1000),
                source="elevenlabs",
                speaker=role,
                text=segment["text"],
            )
            db.session.add(event)
            events.append(event)
        db.session.commit()
        return jsonify({
            "ok": True,
            "provider": "gemini",
            "segments": [
                {"speaker": event.speaker, "text": event.text, "start_ms": event.timestamp_ms}
                for event in events
            ],
        }), 201

    # The SDK needs a real file, so write the bytes to a temp file for the duration of the call.
    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        tmp.write(audio_bytes)
        tmp.seek(0)
        try:
            result = ElevenLabs(api_key=api_key).speech_to_text.convert(
                file=tmp, model_id="scribe_v2", diarize=True
            )
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # Speaker ids are only consistent within this chunk. First voice heard = seller, others = client.
    roles = {}
    events = []
    for segment in _group_words_by_speaker(result.words):
        text = segment["text"].strip()
        if not text:
            continue
        role = roles.setdefault(
            segment["speaker"], "seller" if not roles else "client"
        )
        event = Event(
            session_id=session_id,
            timestamp_ms=offset_ms + int(segment["start"] * 1000),
            source="elevenlabs",
            speaker=role,
            text=text,
        )
        db.session.add(event)
        events.append(event)
    db.session.commit()
    print(
        f"[elevenlabs] session {session_id}: {len(events)} segment(s) from {len(result.words)} words"
    )
    return jsonify(
        {
            "ok": True,
            "segments": [
                {"speaker": event.speaker, "text": event.text, "start_ms": event.timestamp_ms}
                for event in events
            ],
        }
    ), 201
