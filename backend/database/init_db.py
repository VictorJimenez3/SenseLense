# init_db.py
# Creates saleslens.db + tables + helpful views for 20s bucketing (15 min default window)

import os
import sqlite3
import time

DEFAULT_DB_PATH = os.path.join("sync-engine", "data", "adpitch.db")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- 1) One row per meeting/session
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  started_at_epoch_ms INTEGER,
  duration_ms INTEGER DEFAULT 900000,      -- 15 minutes
  bucket_ms INTEGER DEFAULT 20000          -- 20 seconds
);

-- 2) Transcript segments from ElevenLabs STT (batch or realtime committed chunks)
CREATE TABLE IF NOT EXISTS transcript_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  speaker_label TEXT NOT NULL,             -- e.g. SPEAKER_00 / SPEAKER_01
  speaker_role TEXT,                       -- 'seller' or 'client' (filled after mapping)
  text TEXT NOT NULL,
  start_ms INTEGER NOT NULL,               -- ms since session start
  end_ms INTEGER NOT NULL,                 -- ms since session start
  created_at_epoch_ms INTEGER DEFAULT (CAST(strftime('%s','now') AS INTEGER) * 1000),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

-- 3) Mood samples from Presage (store frequently; aggregate later)
CREATE TABLE IF NOT EXISTS mood_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  ts_ms INTEGER NOT NULL,                  -- ms since session start
  target_role TEXT NOT NULL,               -- usually 'client'
  engagement REAL,                         -- 0..1
  valence REAL,                            -- -1..1
  arousal REAL,                            -- 0..1 (optional)
  confidence REAL,                         -- 0..1
  created_at_epoch_ms INTEGER DEFAULT (CAST(strftime('%s','now') AS INTEGER) * 1000),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

-- 4) Map diarized labels to roles (ME vs THEM)
CREATE TABLE IF NOT EXISTS speaker_map (
  session_id TEXT NOT NULL,
  speaker_label TEXT NOT NULL,
  speaker_role TEXT NOT NULL CHECK (speaker_role IN ('seller','client')),
  PRIMARY KEY(session_id, speaker_label),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_ts_session_time ON transcript_segments(session_id, start_ms, end_ms);
CREATE INDEX IF NOT EXISTS idx_mood_session_time ON mood_samples(session_id, ts_ms);
CREATE INDEX IF NOT EXISTS idx_map_session ON speaker_map(session_id);

-- ===== Views for 20-second bucket analysis =====

-- A) Client mood aggregated into 20s buckets
CREATE VIEW IF NOT EXISTS mood_20s AS
SELECT
  session_id,
  (ts_ms / 20000) AS bucket,
  MIN(ts_ms) AS bucket_first_ts,
  AVG(engagement) AS avg_engagement,
  AVG(valence) AS avg_valence,
  AVG(arousal) AS avg_arousal,
  AVG(confidence) AS avg_confidence,
  COUNT(*) AS n_samples
FROM mood_samples
WHERE target_role = 'client'
GROUP BY session_id, bucket;

-- B) Speech segments bucketed by midpoint (simple + fast hackathon join)
CREATE VIEW IF NOT EXISTS speech_bucket AS
SELECT
  session_id,
  ((start_ms + end_ms) / 2) / 20000 AS bucket,
  COALESCE(speaker_role, speaker_label) AS who,     -- falls back if role not mapped yet
  COUNT(*) AS n_segments,
  GROUP_CONCAT(text, ' ') AS text_blob
FROM transcript_segments
GROUP BY session_id, bucket, who;

-- C) The join you will feed to Gemini: seller speech + client mood per bucket
CREATE VIEW IF NOT EXISTS seller_vs_client_mood AS
SELECT
  m.session_id,
  m.bucket,
  m.avg_valence,
  m.avg_engagement,
  m.avg_arousal,
  m.avg_confidence,
  s.text_blob AS seller_text
FROM mood_20s m
JOIN speech_bucket s
  ON s.session_id = m.session_id
 AND s.bucket = m.bucket
WHERE s.who = 'seller'
ORDER BY m.session_id, m.bucket;
"""

import sqlite3
from pathlib import Path

def init_db(db_path: str):
    db_path = Path(db_path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(__file__).resolve().parent / "src" / "schema.sql"
    if not schema_path.exists():
        raise SystemExit(f"schema.sql not found at: {schema_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

        # sanity check
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        print("[ok] DB initialized:", db_path)
        print("[ok] tables:", tables)
    finally:
        conn.close()

if __name__ == "__main__":
    # default location matching your env example
    default_db = Path(__file__).resolve().parent / "data" / "adpitch.db"
    init_db(str(default_db))