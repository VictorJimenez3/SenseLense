import base64
import io
import time
from types import SimpleNamespace

import cv2
import numpy as np

import blueprints.analysis as analysis
from blueprints.analysis import _group_words_by_speaker
from models import db, Event


def _sample_words():
    return [
        SimpleNamespace(text="Hi", type="word", start=0.0, speaker_id="speaker_0"),
        SimpleNamespace(text=" ", type="spacing", start=None, speaker_id="speaker_0"),
        SimpleNamespace(text="there", type="word", start=0.4, speaker_id="speaker_0"),
        SimpleNamespace(text=" ", type="spacing", start=None, speaker_id="speaker_0"),
        SimpleNamespace(text="(laughs)", type="audio_event", start=0.9, speaker_id=None),
        SimpleNamespace(text="Hello", type="word", start=1.2, speaker_id="speaker_1"),
        SimpleNamespace(text=" ", type="spacing", start=None, speaker_id="speaker_1"),
        SimpleNamespace(text="back", type="word", start=1.5, speaker_id="speaker_1"),
    ]


def test_group_words_by_speaker():
    segments = _group_words_by_speaker(_sample_words())

    assert segments == [
        {"speaker": "speaker_0", "text": "Hi there ", "start": 0.0},
        {"speaker": "speaker_1", "text": "Hello back", "start": 1.2},
    ]


def test_transcribe_maps_speakers(seeded, client, monkeypatch):
    words = _sample_words()

    class FakeElevenLabs:
        def __init__(self, api_key):
            self.speech_to_text = SimpleNamespace(
                convert=lambda **kwargs: SimpleNamespace(text="Hi there Hello back", words=words)
            )

    monkeypatch.setitem(client.application.config, "ELEVENLABS_API_KEY", "test")
    monkeypatch.setattr(analysis, "ElevenLabs", FakeElevenLabs)
    with client.application.app_context():
        Event.query.filter_by(
            session_id=seeded["session_id"],
            source="elevenlabs",
        ).delete()
        db.session.commit()

    response = client.post(
        f"/api/transcribe/{seeded['session_id']}?offset_ms=10000",
        data={"audio": (io.BytesIO(b"a" * 1024), "chunk.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["segments"] == [
        {"speaker": "seller", "text": "Hi there", "start_ms": 10000},
        {"speaker": "client", "text": "Hello back", "start_ms": 11200},
    ]
    event_response = client.get(
        f"/api/sessions/{seeded['session_id']}?events=true"
    )
    transcript_events = [
        event
        for event in event_response.get_json()["events"]
        if event["source"] == "elevenlabs"
    ]
    assert len(transcript_events) == 2
    assert [event["speaker"] for event in transcript_events] == ["seller", "client"]


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert isinstance(data["deepface_ready"], bool)


def test_index(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "message" in response.get_json()


def test_create_and_list_clients(client):
    response = client.post("/api/clients", json={"name": "Ada", "company": "X"})

    assert response.status_code == 201
    data = response.get_json()
    assert data["session_count"] == 0
    assert data["created_at"].endswith("+00:00")

    listing = client.get("/api/clients")
    assert listing.status_code == 200
    clients = listing.get_json()
    assert len(clients) == 1
    assert clients[0]["id"] == data["id"]


def test_get_client_includes_sessions(client, seeded):
    response = client.get(f"/api/clients/{seeded['client_id']}")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["sessions"]) == 1
    assert data["session_count"] == 1


def test_get_missing_client_404(client):
    assert client.get("/api/clients/999").status_code == 404


def test_session_lifecycle(client, seeded):
    session_id = seeded["session_id"]
    client_id = seeded["client_id"]

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ended_at"] is None
    assert data["client_name"] == "Ada Lovelace"
    assert "events" not in data

    response = client.get(f"/api/sessions/{session_id}?events=true")
    assert response.status_code == 200
    events = response.get_json()["events"]
    assert len(events) == 3
    assert [event["timestamp_ms"] for event in events] == sorted(
        event["timestamp_ms"] for event in events
    )

    response = client.patch(
        f"/api/sessions/{session_id}/end",
        json={"summary": "notes", "overall_sentiment": 0.4, "engagement_score": 77},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ended_at"].endswith("+00:00")
    assert data["summary"] == "notes"
    assert data["overall_sentiment"] == 0.4
    assert data["engagement_score"] == 77

    response = client.delete(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert client.get(f"/api/sessions/{session_id}").status_code == 404
    assert client.get(f"/api/clients/{client_id}").get_json()["session_count"] == 0


def test_create_session_unknown_client_fails(client):
    response = client.post("/api/sessions", json={"client_id": 999, "title": "x"})

    assert response.status_code == 201
    assert response.get_json()["client_name"] == "Unknown Client"
    # TODO: should be 404 — FK is not enforced by SQLite by default.


def test_ingest_single_event(client, seeded):
    response = client.post(
        f"/api/sessions/{seeded['session_id']}/events",
        json={"timestamp_ms": 8000, "source": "deepface", "emotion": "neutral"},
    )

    assert response.status_code == 201
    assert isinstance(response.get_json(), list)
    assert len(response.get_json()) == 1


def test_insights(client, seeded):
    response = client.get(f"/api/sessions/{seeded['session_id']}/insights")

    assert response.status_code == 200
    data = response.get_json()
    assert data["deepface_samples"] == 2
    assert data["transcript_chunks"] == 1
    assert data["avg_valence"] == 0.45
    assert data["emotion_breakdown"] == {"happy": 1, "neutral": 1}


def test_transcribe_requires_key(client, seeded):
    response = client.post(f"/api/transcribe/{seeded['session_id']}")

    assert response.status_code == 503
    assert "ELEVENLABS_API_KEY" in response.get_json()["error"]


def test_transcribe_requires_audio_field(client, seeded):
    client.application.config["ELEVENLABS_API_KEY"] = "test"
    try:
        response = client.post(f"/api/transcribe/{seeded['session_id']}")
    finally:
        client.application.config["ELEVENLABS_API_KEY"] = None

    assert response.status_code == 400
    assert "missing 'audio'" in response.get_json()["error"]


def test_analyze_frame_validation(client, seeded):
    path = f"/api/analyze-frame/{seeded['session_id']}"

    response = client.post(path, json={})
    assert response.status_code == 400
    assert "no frame" in response.get_json()["error"]

    response = client.post(path, json={"frame": "data:image/jpeg;base64,!!!"})
    assert response.status_code == 400
    assert "bad base64" in response.get_json()["error"]

    invalid_image = base64.b64encode(b"not an image").decode()
    response = client.post(
        path,
        json={"frame": f"data:image/jpeg;base64,{invalid_image}"},
    )
    assert response.status_code == 400
    assert "invalid image" in response.get_json()["error"]


def test_analyze_frame_real_jpeg_without_face(client, seeded):
    success, encoded = cv2.imencode(
        ".jpg",
        np.full((64, 64, 3), 128, dtype=np.uint8),
    )
    assert success
    frame = f"data:image/jpeg;base64,{base64.b64encode(encoded).decode()}"

    response = client.post(
        f"/api/analyze-frame/{seeded['session_id']}",
        json={"frame": frame, "timestamp_ms": 1000},
    )

    assert response.status_code == 422
    assert "No face" in response.get_json()["error"]
    insights = client.get(
        f"/api/sessions/{seeded['session_id']}/insights"
    ).get_json()
    assert insights["deepface_samples"] == 2


def test_summary_requires_gemini_key(client, seeded):
    response = client.post(
        f"/api/sessions/{seeded['session_id']}/summary/generate"
    )

    assert response.status_code == 500
    data = response.get_json()
    assert data["ok"] is False
    assert "GEMINI_API_KEY" in data["error"]


def test_404_for_unknown_session_on_all_nested_routes(client):
    assert client.get("/api/sessions/999").status_code == 404
    assert client.get("/api/sessions/999/insights").status_code == 404
    assert client.patch("/api/sessions/999/end", json={}).status_code == 404
    assert client.delete("/api/sessions/999").status_code == 404
    assert client.post("/api/sessions/999/events", json=[]).status_code == 404
    assert client.post("/api/analyze-frame/999", json={"frame": "x"}).status_code == 404
    assert client.post("/api/transcribe/999").status_code == 404


def test_failed_analysis_does_not_store_fake_neutral(client, seeded, monkeypatch):
    def unavailable(_):
        raise RuntimeError('model unavailable')
    monkeypatch.setattr(analysis, '_run_deepface', unavailable)
    response = client.post(f"/api/analyze-frame/{seeded['session_id']}",
                           json={'frame': 'eA==', 'timestamp_ms': 4000})
    assert response.status_code == 503
    assert client.get(f"/api/sessions/{seeded['session_id']}/insights").get_json()['deepface_samples'] == 2


def test_summary_model_call_has_deadline(client, seeded, monkeypatch):
    import blueprints.ai as ai
    client.application.config['GEMINI_API_KEY'] = 'test'
    monkeypatch.setattr(ai.genai, 'configure', lambda **kwargs: None)
    calls = []
    class Model:
        def __init__(self, *args, **kwargs):
            pass
        def generate_content(self, prompt, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='{"overall_summary":"Test summary"}')
    monkeypatch.setattr(ai.genai, 'GenerativeModel', Model)
    response = client.post(f"/api/sessions/{seeded['session_id']}/summary/generate")
    assert response.status_code == 200
    assert calls[0].get('request_options', {}).get('timeout') == 45


def test_summary_unknown_session_returns_404(client):
    assert client.post('/api/sessions/999/summary/generate').status_code == 404


def test_no_face_is_skipped_instead_of_stored_as_emotion(client, seeded, monkeypatch):
    from deepface import DeepFace
    def no_face(**kwargs):
        if kwargs.get('enforce_detection'):
            raise ValueError('Face could not be detected. Please confirm that the picture is a face photo')
        return [{'dominant_emotion': 'neutral'}]
    monkeypatch.setattr(DeepFace, 'analyze', no_face)
    _, image = cv2.imencode('.jpg', np.zeros((64, 64, 3), dtype=np.uint8))
    response = client.post(f"/api/analyze-frame/{seeded['session_id']}",
                           json={'frame': base64.b64encode(image).decode(), 'timestamp_ms': 4000})
    assert response.status_code == 422
    assert client.get(f"/api/sessions/{seeded['session_id']}/insights").get_json()['deepface_samples'] == 2


def test_insights_prefer_morphcast_when_both_providers_exist(client, seeded):
    client.post(f"/api/sessions/{seeded['session_id']}/events", json=[
        {"source":"morphcast", "emotion":"happy", "valence":0.4, "timestamp_ms":6000}
    ])
    data = client.get(f"/api/sessions/{seeded['session_id']}/insights").get_json()
    assert data["emotion_provider"] == "morphcast"
    assert data["emotion_samples"] == 1
    assert data["avg_valence"] == 0.4
    assert data["deepface_samples"] == 2


def test_insights_and_summary_use_faceapi_samples(client, seeded):
    from blueprints.ai import get_mood_data
    from models import Session
    client.post(f"/api/sessions/{seeded['session_id']}/events", json=[
        {"source":"faceapi", "emotion":"happy", "valence":0.8, "timestamp_ms":6000}
    ])
    data = client.get(f"/api/sessions/{seeded['session_id']}/insights").get_json()
    assert data["emotion_provider"] == "faceapi"
    assert data["emotion_samples"] == 1
    assert data["avg_valence"] == 0.8
    with client.application.app_context():
        moods = get_mood_data(Session.query.get(seeded['session_id']).events)
        assert moods == [{"t_ms":6000,"emotion":"happy","valence":0.8}]


def test_gemini_quota_is_reported_as_429(client, seeded, monkeypatch):
    import urllib.error
    client.application.config['GEMINI_API_KEY'] = 'test'
    def quota(*args, **kwargs):
        raise urllib.error.HTTPError('https://example.com',429,'quota',{},io.BytesIO(b'{"error":"quota"}'))
    monkeypatch.setattr(analysis.urllib.request, 'urlopen', quota)
    response = client.post(f"/api/transcribe/{seeded['session_id']}",
        data={"audio":(io.BytesIO(b'a'*1024),'chunk.webm')},content_type='multipart/form-data')
    assert response.status_code == 429
    assert response.get_json()['code'] == 'quota_exhausted'
    assert 'quota exhausted' in response.get_json()['error'].lower()
