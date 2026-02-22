"""
presage_capture.py — Facial emotion capture using DeepFace + OpenCV
Runs as a background thread during a session, sampling webcam every 2.4 s
and POSTing emotion events to the Flask /api/sessions/<id>/events endpoint.

Usage (standalone test):
    python3 presage_capture.py --session-id 1 --duration 30

Usage (from app):
    from presage_capture import PresageCapture
    cap = PresageCapture(session_id=1, flask_url="http://localhost:5050")
    cap.start()   # non-blocking
    ...
    cap.stop()
"""

import argparse
import time
import threading
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# DeepFace + cv2 — install via: pip install deepface opencv-python-headless tf-keras
try:
    import cv2
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("[presage] WARNING: deepface/cv2 not installed. Run: pip install deepface opencv-python-headless tf-keras")

# ── Emotion → valence mapping (rough approximation) ──────────────────────────
EMOTION_VALENCE = {
    "happy":     0.9,
    "surprise":  0.3,
    "neutral":   0.0,
    "sad":      -0.5,
    "disgust":  -0.7,
    "fear":     -0.6,
    "angry":    -0.8,
}

# Map DeepFace emotion labels → your app's labels
EMOTION_MAP = {
    "happy":    "happy",
    "surprise": "engaged",
    "neutral":  "neutral",
    "sad":      "negative",
    "disgust":  "negative",
    "fear":     "confused",
    "angry":    "negative",
}


class PresageCapture:
    """
    Captures webcam frames at `interval_ms` intervals, runs DeepFace emotion
    analysis, and POSTs results to Flask.
    """

    def __init__(
        self,
        session_id: int,
        flask_url: str = "http://localhost:5050",
        interval_ms: int = 2400,
        camera_index: int = 0,
    ):
        self.session_id = session_id
        self.flask_url = flask_url.rstrip("/")
        self.interval_s = interval_ms / 1000
        self.camera_index = camera_index
        self._stop_event = threading.Event()
        self._thread = None
        self._session_start_ms = int(time.time() * 1000)

    def start(self):
        """Start capturing in a background thread (non-blocking)."""
        if not DEEPFACE_AVAILABLE:
            print("[presage] Cannot start — install deepface + opencv-python-headless first")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[presage] Started capture for session {self.session_id} @ {self.interval_s}s intervals")

    def stop(self):
        """Signal the capture thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[presage] Stopped")

    def _run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("[presage] ERROR: Could not open camera")
            return

        try:
            while not self._stop_event.is_set():
                loop_start = time.time()

                ret, frame = cap.read()
                if not ret:
                    print("[presage] Camera read failed, retrying…")
                    time.sleep(0.5)
                    continue

                # Run DeepFace emotion analysis on the frame
                emotion, valence = self._analyze(frame)
                timestamp_ms = int(time.time() * 1000) - self._session_start_ms

                # POST to Flask
                self._post_event(timestamp_ms, emotion, valence)

                # Sleep remainder of interval
                elapsed = time.time() - loop_start
                sleep_for = max(0, self.interval_s - elapsed)
                self._stop_event.wait(timeout=sleep_for)

        finally:
            cap.release()

    def _analyze(self, frame):
        """Run DeepFace on a single BGR frame. Returns (emotion_label, valence)."""
        try:
            result = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                enforce_detection=False,  # don't crash if face not detected
                silent=True,
            )
            # result is a list when multiple faces; take first
            if isinstance(result, list):
                result = result[0]

            dominant = result.get("dominant_emotion", "neutral").lower()
            mapped = EMOTION_MAP.get(dominant, "neutral")
            valence = EMOTION_VALENCE.get(dominant, 0.0)
            print(f"[presage] {dominant} → {mapped} (valence={valence:+.2f})")
            return mapped, valence

        except Exception as e:
            print(f"[presage] Analysis error: {e}")
            return "neutral", 0.0

    def _post_event(self, timestamp_ms: int, emotion: str, valence: float):
        """POST a single presage event to Flask."""
        payload = {
            "timestamp_ms": timestamp_ms,
            "source": "presage",
            "emotion": emotion,
            "valence": valence,
        }
        try:
            r = requests.post(
                f"{self.flask_url}/api/sessions/{self.session_id}/events",
                json=[payload],  # endpoint accepts a list
                timeout=3,
            )
            if r.status_code not in (200, 201):
                print(f"[presage] POST failed: {r.status_code} {r.text[:80]}")
        except requests.RequestException as e:
            print(f"[presage] POST error: {e}")


# ── Flask Integration Helpers ─────────────────────────────────────────────────

# Global registry so the Flask /api/record endpoint can manage capture instances
_active_captures: dict[int, PresageCapture] = {}


def start_presage_for_session(session_id: int, flask_url: str = "http://localhost:5050") -> bool:
    """Start a PresageCapture for a session. Called from Flask /api/record."""
    if session_id in _active_captures:
        return False  # already running
    cap = PresageCapture(session_id=session_id, flask_url=flask_url)
    cap.start()
    _active_captures[session_id] = cap
    return True


def stop_presage_for_session(session_id: int) -> bool:
    """Stop capture for a session. Called from Flask /api/sessions/<id>/end."""
    cap = _active_captures.pop(session_id, None)
    if cap:
        cap.stop()
        return True
    return False


# ── Standalone CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Presage-style facial emotion capture")
    parser.add_argument("--session-id", type=int, required=True, help="Flask session ID")
    parser.add_argument("--duration", type=int, default=30, help="Capture duration in seconds")
    parser.add_argument("--flask-url", default="http://localhost:5050", help="Flask base URL")
    parser.add_argument("--interval-ms", type=int, default=2400, help="Sample interval in ms")
    args = parser.parse_args()

    cap = PresageCapture(
        session_id=args.session_id,
        flask_url=args.flask_url,
        interval_ms=args.interval_ms,
    )
    cap.start()
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        pass
    cap.stop()
