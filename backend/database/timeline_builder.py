"""
sync-engine/src/timeline_builder.py — Merges physiology + transcript into a single timeline.

THIS IS THE CORE SYNC LOGIC. It answers the question:
"What was the customer's body doing when they said X?"

HOW IT WORKS:
1. Get all transcript segments for a session (ordered by time)
2. For each segment, find all physiology readings in the same time window
3. Average the physiology values across that window
4. Return a merged timeline: [{text, speaker, physiology}, ...]

EXAMPLE OUTPUT:
    {
        "start_ms": 1708534891500,
        "end_ms": 1708534896000,
        "speaker": "customer",
        "text": "The pricing seems really high for what we get",
        "physiology": {
            "heart_rate": 81.2,       ← HR spiked here!
            "hrv": 35.4,              ← HRV dropped (stress)
            "breathing_rate": 18.1,
            "emotion_score": -0.4,    ← Negative emotion
            "engagement": 0.62        ← Engagement declining
        }
    }
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from sync_engine_path import *
import db_manager


def build_timeline(session_id: str) -> list[dict]:
    """
    Build a merged timeline for a completed session.

    Returns a list of entries, each combining a transcript segment
    with the averaged physiology data from the same time window.
    """
    segments = db_manager.get_transcript_for_session(session_id)

    if not segments:
        return []

    timeline = []

    for seg in segments:
        start_ms = seg["timestamp_start_ms"]
        end_ms = seg["timestamp_end_ms"]

        # Find physiology readings that overlap this transcript segment
        physio_readings = db_manager.get_physiology_in_range(session_id, start_ms, end_ms)

        # Average the physiology values across the window
        physiology = _average_physiology(physio_readings)

        timeline.append({
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker": seg["speaker"],
            "text": seg["text"],
            "physiology": physiology
        })

    return timeline


def _average_physiology(readings: list[dict]) -> dict:
    """Average physiology readings across a time window."""
    if not readings:
        return {
            "heart_rate": None,
            "hrv": None,
            "breathing_rate": None,
            "phasic": None,
            "emotion_score": None,
            "engagement": None,
        }

    fields = ["heart_rate", "hrv", "breathing_rate", "phasic", "emotion_score", "engagement"]
    result = {}

    for field in fields:
        values = [r[field] for r in readings if r.get(field) is not None]
        result[field] = round(sum(values) / len(values), 2) if values else None

    return result


def format_timeline_for_display(timeline: list[dict], session_start_ms: int) -> str:
    """Format timeline as human-readable text (for Claude prompt or debugging)."""
    lines = []
    for entry in timeline:
        offset_sec = (entry["start_ms"] - session_start_ms) / 1000
        minutes = int(offset_sec // 60)
        seconds = offset_sec % 60

        physio = entry["physiology"]
        physio_str = ", ".join(
            f"{k}: {v}" for k, v in physio.items() if v is not None
        )

        lines.append(
            f"[{minutes:02d}:{seconds:05.2f}] {entry['speaker'].upper()}: \"{entry['text']}\"\n"
            f"    → {physio_str}"
        )

    return "\n\n".join(lines)


if __name__ == "__main__":
    # Quick test: build timeline for the most recent session
    sessions = db_manager.list_sessions()
    if sessions:
        session = sessions[0]
        timeline = build_timeline(session["session_id"])
        print(format_timeline_for_display(timeline, session["start_time_ms"]))
    else:
        print("No sessions found. Start a recording first.")
