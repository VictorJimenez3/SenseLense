# FILE: api.py - The logic center. This is where you plug in Presage and ElevenLabs data.
from flask import Blueprint, jsonify, request
from models import db, Client, Session, Event
from datetime import datetime

api_bp = Blueprint("api", __name__)


# ── Health ────────────────────────────────────────────────────────────────────

@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


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
    """
    Accepts a list of event objects.
    Each event: { timestamp_ms, source, emotion?, valence?, speaker?, text? }
    This is the integration point for future Presage + ElevenLabs data pipelines.
    """
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


# ── Insights (AI pipeline hook) ───────────────────────────────────────────────

@api_bp.get("/sessions/<int:session_id>/insights")
def get_insights(session_id):
    """
    Hook point for the AI insights pipeline.
    Currently returns the stored summary + computed stats.
    Wire in your pipeline (pipelines/insights.py) here when ready.
    """
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
