# FILE: models.py - Database blueprint. Defines tables for Clients, Sessions, and ElevenLabs/Presage events.
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Client(db.Model):
    """A customer / prospect the sales team meets with."""
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    email = db.Column(db.String(120))
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("Session", back_populates="client", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "session_count": len(self.sessions),
        }


class Session(db.Model):
    """
    A recorded sales session.
    Holds a timeline of synced Presage emotion events + ElevenLabs transcript chunks.
    """
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    title = db.Column(db.String(200), default="Meeting")
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    summary = db.Column(db.Text, default="")          # AI insight summary (populated post-session)
    overall_sentiment = db.Column(db.Float, default=0.0)  # -1.0 (negative) → 1.0 (positive)
    engagement_score = db.Column(db.Float, default=0.0)   # 0–100

    client = db.relationship("Client", back_populates="sessions")
    events = db.relationship("Event", back_populates="session", cascade="all, delete-orphan", order_by="Event.timestamp_ms")

    def to_dict(self, include_events=False):
        data = {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else "Unknown Client",
            "title": self.title,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "summary": self.summary,
            "overall_sentiment": self.overall_sentiment,
            "engagement_score": self.engagement_score,
        }
        if include_events:
            data["events"] = [e.to_dict() for e in self.events]
        return data


class Event(db.Model):
    """
    A single timestamped event on the session timeline.
    source: 'presage' (emotion/reaction) | 'elevenlabs' (transcript chunk)
    """
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    timestamp_ms = db.Column(db.Integer, nullable=False)   # ms since session start
    source = db.Column(db.String(30), nullable=False)       # 'presage' | 'elevenlabs'

    # Presage fields
    emotion = db.Column(db.String(40))          # e.g. "happy", "neutral", "confused"
    valence = db.Column(db.Float)               # -1.0 → 1.0

    # ElevenLabs / transcript fields
    speaker = db.Column(db.String(20))          # 'rep' | 'client'
    text = db.Column(db.Text)

    session = db.relationship("Session", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp_ms": self.timestamp_ms,
            "source": self.source,
            "emotion": self.emotion,
            "valence": self.valence,
            "speaker": self.speaker,
            "text": self.text,
        }
