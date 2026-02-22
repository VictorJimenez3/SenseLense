# FILE: app.py - Main entry point. Starts the Flask server.
import os
import threading
import subprocess

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from models import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)

    from blueprints.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    try:
        from AI.ai import ai_bp
        app.register_blueprint(ai_bp, url_prefix="/api")
        print("[AI] Gemini AI blueprint loaded successfully.")
    except Exception as e:
        print(f"[AI] Not available: {e}")

    # Import presage helpers (gracefully handles missing deepface/cv2)
    try:
        from presage_capture import start_presage_for_session, stop_presage_for_session
        _presage_available = True
    except Exception as e:
        print(f"[presage] Not available: {e}")
        _presage_available = False
        def start_presage_for_session(*a, **kw): return False
        def stop_presage_for_session(*a, **kw): return False

    # ── /api/record — Start transcription + Presage when Record is clicked ──
    @app.route('/api/record', methods=['POST'])
    def start_recording():
        data = request.get_json(force=True) or {}
        session_id = data.get("session_id")
        record_seconds = str(data.get("record_seconds", 900))
        flask_url = request.host_url.rstrip("/")  # e.g. http://localhost:5050

        # 1) Start ElevenLabs transcription in a subprocess
        def run_transcription():
            script_path = os.path.join(os.path.dirname(__file__), "Transcriptions", "main.py")
            env = os.environ.copy()
            env["SESSION_ID"] = str(session_id)
            env["RECORD_SECONDS"] = record_seconds
            env["ADPitch_DB"] = os.path.join(os.path.dirname(__file__), "instance", "senselense.db")
            print(f"[record] Starting ElevenLabs transcription for session {session_id}")
            subprocess.run(
                ["python3", script_path],
                cwd=os.path.join(os.path.dirname(__file__), "Transcriptions"),
                env=env,
            )

        threading.Thread(target=run_transcription, daemon=True).start()

        # 2) Start Presage facial emotion capture
        if _presage_available and session_id:
            started = start_presage_for_session(int(session_id), flask_url=flask_url)
            print(f"[presage] Capture started for session {session_id}: {started}")

        return jsonify({
            "status": "recording triggered",
            "session_id": session_id,
            "presage": _presage_available,
        }), 200

    # ── Patch end session to also stop Presage ────────────────────────────────
    # We hook into the PATCH /api/sessions/<id>/end by overriding after_request
    # so we don't duplicate the end_session logic already in blueprints/api.py
    @app.after_request
    def stop_presage_on_end(response):
        if (request.method == "PATCH"
                and "/sessions/" in request.path
                and request.path.endswith("/end")
                and response.status_code == 200):
            try:
                seg = request.path.strip("/").split("/")
                # path: api/sessions/<id>/end
                sid = int(seg[seg.index("sessions") + 1])
                stop_presage_for_session(sid)
            except Exception:
                pass
        return response

    with app.app_context():
        db.create_all()

    return app


app = create_app()
