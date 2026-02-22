import os
import sqlite3
from pathlib import Path
import json


def upsert_speaker_map(db_path: str, session_id: str, seller_label: str, client_label: str):
    """
    Store diarization label -> role mapping in speaker_map.
    seller_label/client_label are diarization labels like 'spk_0', 'spk_1'.
    """
    db_path = _normalize_db_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        conn.execute(
            "INSERT OR REPLACE INTO speaker_map(session_id, diar_label, role) VALUES (?, ?, 'seller')",
            (session_id, seller_label),
        )
        conn.execute(
            "INSERT OR REPLACE INTO speaker_map(session_id, diar_label, role) VALUES (?, ?, 'customer')",
            (session_id, client_label),
        )
        conn.commit()
    finally:
        conn.close()

def apply_speaker_map_to_segments(db_path: str, session_id: str):
    """
    Update transcript_segments.speaker using the diarization label stored in raw_json.
    We expect raw_json to contain {"speaker_label": "..."}.
    """
    db_path = _normalize_db_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        # SQLite json_extract works only if JSON1 extension is enabled (common, but not guaranteed).
        # We'll implement a safe Python fallback if JSON1 isn't present.
        try:
            conn.execute(
                """
                UPDATE transcript_segments
                SET speaker = (
                    SELECT role
                    FROM speaker_map
                    WHERE speaker_map.session_id = transcript_segments.session_id
                      AND speaker_map.diar_label = json_extract(transcript_segments.raw_json, '$.speaker_label')
                )
                WHERE session_id = ?
                """,
                (session_id,),
            )
            conn.commit()
            return
        except sqlite3.OperationalError:
            # JSON1 not available; do Python-based update
            rows = conn.execute(
                "SELECT id, raw_json FROM transcript_segments WHERE session_id = ?",
                (session_id,),
            ).fetchall()

            mapping = dict(conn.execute(
                "SELECT diar_label, role FROM speaker_map WHERE session_id = ?",
                (session_id,),
            ).fetchall())

            updates = []
            for seg_id, raw_json_str in rows:
                if not raw_json_str:
                    continue
                try:
                    payload = json.loads(raw_json_str)
                except Exception:
                    continue
                diar = payload.get("speaker_label")
                role = mapping.get(diar)
                if role:
                    updates.append((role, seg_id))

            conn.executemany("UPDATE transcript_segments SET speaker = ? WHERE id = ?", updates)
            conn.commit()
    finally:
        conn.close()
def _normalize_db_path(db_path: str) -> str:
    if not db_path or not str(db_path).strip():
        raise RuntimeError("db_path is empty")

    p = Path(os.path.expandvars(os.path.expanduser(str(db_path).strip())))
    if not p.is_absolute():
        repo_root = Path(__file__).resolve().parents[2]
        p = (repo_root / p).resolve()

    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)

def insert_transcript_segments(db_path: str, segments):
    db_path = _normalize_db_path(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        rows = []
        for s in segments:
            raw = {
                "speaker_label": s.get("speaker_label"),
                "start_ms": s.get("start_ms"),
                "end_ms": s.get("end_ms"),
            }
            rows.append((
                s["session_id"],
                int(s["start_ms"]),
                int(s["end_ms"]),
                "unknown",
                s["text"],
                None,
                json.dumps(raw, ensure_ascii=False),
            ))

        conn.executemany(
            """
            INSERT INTO transcript_segments(
              session_id, timestamp_start_ms, timestamp_end_ms,
              speaker, text, confidence, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

def insert_transcript_segments(db_path: str, segments):
    """
    Matches schema.sql transcript_segments table:
      session_id
      timestamp_start_ms
      timestamp_end_ms
      speaker  (seller/customer/unknown)
      text
      confidence
      raw_json
    Your transcription segments currently contain speaker_label; we'll store speaker='unknown'
    and keep the diarization label inside raw_json so you don't lose info.
    """
    db_path = _normalize_db_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        rows = []
        for s in segments:
            raw = {
                "speaker_label": s.get("speaker_label"),
                "start_ms": s.get("start_ms"),
                "end_ms": s.get("end_ms"),
            }
            rows.append((
                s["session_id"],
                int(s["start_ms"]),
                int(s["end_ms"]),
                "unknown",           # schema speaker is seller/customer/unknown
                s["text"],
                None,                # confidence (optional)
                str(raw),            # raw_json (cheap debugging, can be json.dumps if you want)
            ))

        conn.executemany(
            """
            INSERT INTO transcript_segments(
              session_id, timestamp_start_ms, timestamp_end_ms,
              speaker, text, confidence, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

def upsert_speaker_map(*args, **kwargs):
    """
    Your current schema.sql does NOT have speaker_map or speaker_label/speaker_role columns.
    So this function cannot work unless you extend the schema.

    For now, keep it as a no-op so the pipeline doesn't crash.
    """
    return

# ─────────────────────────────────────────────────────────────
# Analytics helpers (Gemini outputs + mood_timeseries)
# ─────────────────────────────────────────────────────────────

import json
from typing import Any, Dict, Optional, List, Tuple


def compute_and_write_mood_timeseries(
    db_path: str,
    session_id: str,
    window_ms: int = 10_000,
    subject_role: str = "customer",
    source: str = "presage",
    delete_existing: bool = True,
) -> int:
    """
    Reads physiology_events for a session and writes aggregated rows to mood_timeseries.

    physiology_events expected columns:
      - session_id
      - timestamp_ms
      - emotion_score (REAL)
      - engagement (REAL)
      - blink_rate (REAL)
      - is_talking (BOOLEAN-ish)
    """
    db_path = _normalize_db_path(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        rows: List[Tuple[int, Optional[float], Optional[float], Optional[float], Optional[int]]] = conn.execute(
            """
            SELECT timestamp_ms, emotion_score, engagement, blink_rate, is_talking
            FROM physiology_events
            WHERE session_id = ?
            ORDER BY timestamp_ms ASC
            """,
            (session_id,),
        ).fetchall()

        if not rows:
            return 0

        # bucket samples into fixed windows using integer division
        buckets: Dict[int, Dict[str, Any]] = {}
        for ts, emo, eng, br, talking in rows:
            window_start = (int(ts) // window_ms) * window_ms
            agg = buckets.get(window_start)
            if agg is None:
                agg = buckets[window_start] = {
                    "sum_emo": 0.0,
                    "sum_eng": 0.0,
                    "sum_br": 0.0,
                    "talk_count": 0,
                    "count_emo": 0,
                    "count_eng": 0,
                    "count_br": 0,
                    "n": 0,
                }

            agg["n"] += 1
            if emo is not None:
                agg["sum_emo"] += float(emo)
                agg["count_emo"] += 1
            if eng is not None:
                agg["sum_eng"] += float(eng)
                agg["count_eng"] += 1
            if br is not None:
                agg["sum_br"] += float(br)
                agg["count_br"] += 1
            if talking is not None and int(talking) == 1:
                agg["talk_count"] += 1

        if delete_existing:
            conn.execute(
                "DELETE FROM mood_timeseries WHERE session_id = ? AND subject_role = ? AND source = ?",
                (session_id, subject_role, source),
            )

        out_rows = []
        for window_start in sorted(buckets.keys()):
            agg = buckets[window_start]
            window_end = window_start + window_ms

            mood_score = (agg["sum_emo"] / agg["count_emo"]) if agg["count_emo"] else None
            engagement = (agg["sum_eng"] / agg["count_eng"]) if agg["count_eng"] else None
            blink_rate = (agg["sum_br"] / agg["count_br"]) if agg["count_br"] else None
            is_talking_pct = (agg["talk_count"] / agg["n"]) if agg["n"] else 0.0

            out_rows.append((
                session_id,
                subject_role,
                int(window_start),
                int(window_end),
                mood_score,
                engagement,
                blink_rate,
                is_talking_pct,
                int(agg["n"]),
                source,
            ))

        conn.executemany(
            """
            INSERT INTO mood_timeseries(
              session_id, subject_role, window_start_ms, window_end_ms,
              mood_score, engagement, blink_rate, is_talking_pct,
              sample_count, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            out_rows,
        )
        conn.commit()
        return len(out_rows)

    finally:
        conn.close()


def insert_gemini_output(
    db_path: str,
    session_id: str,
    target_role: str,                 # 'customer' | 'seller' | 'overall'
    summary_md: str,
    raw_json: Dict[str, Any],
    *,
    prompt_version: Optional[str] = None,
    model: str = "gemini",
    model_version: Optional[str] = None,
    key_points: Optional[str] = None,
    action_items: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    engagement_score: Optional[float] = None,
    risk_score: Optional[float] = None,
) -> None:
    """
    Writes Gemini output (summary + optional metrics) into gemini_outputs.
    raw_json should be the full Gemini response dict.
    """
    db_path = _normalize_db_path(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        conn.execute(
            """
            INSERT INTO gemini_outputs(
              session_id, target_role, prompt_version, model, model_version,
              summary_md, key_points, action_items,
              sentiment_score, engagement_score, risk_score,
              raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                target_role,
                prompt_version,
                model,
                model_version,
                summary_md,
                key_points,
                action_items,
                sentiment_score,
                engagement_score,
                risk_score,
                json.dumps(raw_json, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()