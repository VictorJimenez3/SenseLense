"""CRUD endpoints: clients, sessions, events, insights. Pure Flask + SQLAlchemy — no ML here."""
from datetime import datetime

from flask import Blueprint, jsonify, request

from models import db, Client, Session, Event
from blueprints.analysis import deepface_ready

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "deepface_ready": deepface_ready()})


@api_bp.get("/clients")
def list_clients():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    return jsonify([client.to_dict() for client in clients])


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
    data["sessions"] = [session.to_dict() for session in client.sessions]
    return jsonify(data)


@api_bp.get("/sessions")
def list_sessions():
    sessions = Session.query.order_by(Session.started_at.desc()).all()
    return jsonify([session.to_dict() for session in sessions])


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


@api_bp.delete("/sessions/<int:session_id>")
def delete_session(session_id):
    session = Session.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"ok": True})


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
    return jsonify([event.to_dict() for event in created]), 201


@api_bp.get("/sessions/<int:session_id>/insights")
def get_insights(session_id):
    session = Session.query.get_or_404(session_id)
    events = session.events
    deepface_events = [
        event for event in events
        if event.source == "deepface" and event.valence is not None
    ]
    morphcast_events = [event for event in events
                       if event.source == "morphcast" and event.valence is not None]
    faceapi_events = [event for event in events
                      if event.source == "faceapi" and event.valence is not None]
    emotion_events = faceapi_events or morphcast_events or deepface_events
    elevenlabs_events = [
        event for event in events if event.source == "elevenlabs"
    ]

    avg_valence = (
        sum(event.valence for event in emotion_events) / len(emotion_events)
        if emotion_events else 0.0
    )
    emotion_counts = {}
    for event in emotion_events:
        if event.emotion:
            emotion_counts[event.emotion] = emotion_counts.get(event.emotion, 0) + 1

    return jsonify({
        "session_id": session_id,
        "summary": session.summary,
        "overall_sentiment": session.overall_sentiment,
        "engagement_score": session.engagement_score,
        "avg_valence": round(avg_valence, 3),
        "emotion_breakdown": emotion_counts,
        "transcript_chunks": len(elevenlabs_events),
        "deepface_samples": len(deepface_events),
        "morphcast_samples": len(morphcast_events),
        "faceapi_samples": len(faceapi_events),
        "emotion_samples": len(emotion_events),
        "emotion_provider": "faceapi" if faceapi_events else "morphcast" if morphcast_events else "deepface" if deepface_events else None,
    })
