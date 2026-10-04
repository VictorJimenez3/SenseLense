import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app import app as flask_app  # noqa: E402
from models import db, Client, Session, Event  # noqa: E402


@pytest.fixture()
def client():
    flask_app.config.update(
        TESTING=True,
        ELEVENLABS_API_KEY=None,
        GEMINI_API_KEY=None,
    )
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
    yield flask_app.test_client()


@pytest.fixture()
def seeded(client):
    """One client, session, two DeepFace events, and one transcript event."""
    client_record = client.post(
        "/api/clients",
        json={"name": "Ada Lovelace", "company": "Analytical"},
    ).get_json()
    session = client.post(
        "/api/sessions",
        json={"client_id": client_record["id"], "title": "Discovery"},
    ).get_json()
    client.post(
        f"/api/sessions/{session['id']}/events",
        json=[
            {
                "timestamp_ms": 0,
                "source": "deepface",
                "emotion": "happy",
                "valence": 0.9,
            },
            {
                "timestamp_ms": 2400,
                "source": "deepface",
                "emotion": "neutral",
                "valence": 0.0,
            },
            {
                "timestamp_ms": 5000,
                "source": "elevenlabs",
                "speaker": "client",
                "text": "What about pricing?",
            },
        ],
    )
    return {"client_id": client_record["id"], "session_id": session["id"]}
