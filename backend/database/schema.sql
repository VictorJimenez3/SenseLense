-- sync-engine/src/schema.sql
-- ═══════════════════════════════════════════════════════════
-- ADPitch Database Schema
-- ═══════════════════════════════════════════════════════════
--
-- This is the CONTRACT between all modules. If you change this,
-- tell the whole team.
--
-- WHO WRITES WHAT:
--   sessions            → api-server (create/update)
--   physiology_events   → presage-capture (insert during recording)
--   transcript_segments → transcription (insert during recording)
--   insights            → insights-engine (insert after analysis)
--
-- HOW SYNC WORKS:
--   Both physiology_events and transcript_segments have UTC
--   millisecond timestamps. The sync-engine merges them by
--   finding physiology readings that OVERLAP each transcript
--   segment's time window.

PRAGMA journal_mode=WAL;  -- Allow concurrent reads + writes
PRAGMA busy_timeout=5000; -- Wait up to 5s if DB is locked

-- ─── Sessions ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    customer_name TEXT,
    start_time_ms INTEGER NOT NULL,
    end_time_ms   INTEGER,
    status        TEXT DEFAULT 'recording'
                  CHECK(status IN ('recording','completed','analyzing','analyzed','error')),
    notes         TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─── Physiology Events (from Presage) ──────────────────────
-- Written by: presage-capture/src/db_writer.cpp
-- ~1 row per second during recording

CREATE TABLE IF NOT EXISTS physiology_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    timestamp_ms    INTEGER NOT NULL,   -- UTC millis — THE SYNC KEY
    emotion_score   REAL,               -- -1.0 to 1.0
    engagement      REAL,               -- 0.0 to 1.0
    blink_rate      REAL,               -- Blinks per minute
    is_talking      BOOLEAN,            -- Is subject currently speaking?
    raw_json        TEXT                 -- Full Presage output for debugging
);

-- ─── Transcript Segments (from ElevenLabs) ─────────────────
-- Written by: transcription/src/realtime_transcriber.py
-- ~1 row per utterance/sentence

CREATE TABLE IF NOT EXISTS transcript_segments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id         TEXT NOT NULL REFERENCES sessions(session_id),
    timestamp_start_ms INTEGER NOT NULL,  -- UTC millis — start of utterance
    timestamp_end_ms   INTEGER NOT NULL,  -- UTC millis — end of utterance
    speaker            TEXT NOT NULL DEFAULT 'unknown'
                       CHECK(speaker IN ('seller','customer','unknown')),
    text               TEXT NOT NULL,
    confidence         REAL,
    raw_json           TEXT
);

-- ─── AI Insights (from Claude) ─────────────────────────────
-- Written by: insights-engine/src/analyzer.py
-- Created after session ends and analysis runs

CREATE TABLE IF NOT EXISTS insights (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       TEXT NOT NULL REFERENCES sessions(session_id),
    insight_type     TEXT NOT NULL
                     CHECK(insight_type IN ('coaching','risk','highlight','summary')),
    title            TEXT,
    body             TEXT NOT NULL,
    severity         TEXT DEFAULT 'neutral'
                     CHECK(severity IN ('positive','neutral','concern','critical')),
    timestamp_ref_ms INTEGER,       -- What moment this insight references
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─── Indexes for fast timeline queries ─────────────────────
-- These are CRITICAL for the sync-engine's merge performance.

CREATE INDEX IF NOT EXISTS idx_physio_session_time
    ON physiology_events(session_id, timestamp_ms);

CREATE INDEX IF NOT EXISTS idx_transcript_session_time
    ON transcript_segments(session_id, timestamp_start_ms);

CREATE INDEX IF NOT EXISTS idx_insights_session
    ON insights(session_id);

-- ─── Speaker Map (diarization label -> role) ─────────────────
-- Written by: transcription (heuristic mapping) or UI (manual fix)
-- Allows mapping diarized speakers (e.g., "spk_0") to app roles.

CREATE TABLE IF NOT EXISTS speaker_map (
    session_id     TEXT NOT NULL REFERENCES sessions(session_id),
    diar_label     TEXT NOT NULL,  -- diarization label like "spk_0"
    role           TEXT NOT NULL CHECK(role IN ('seller','customer')),
    PRIMARY KEY (session_id, diar_label)
);

CREATE INDEX IF NOT EXISTS idx_speaker_map_session
    ON speaker_map(session_id);


-- ───────────────────────────────────────────────────────────
-- Gemini outputs (AI summaries)
-- ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gemini_outputs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    TEXT NOT NULL REFERENCES sessions(session_id),

  target_role   TEXT NOT NULL CHECK(target_role IN ('customer','seller','overall')),
  prompt_version TEXT,
  model         TEXT NOT NULL DEFAULT 'gemini',
  model_version TEXT,

  summary_md    TEXT NOT NULL,       -- narrative summary (markdown)
  key_points    TEXT,                -- optional markdown or JSON string
  action_items  TEXT,                -- optional markdown or JSON string

  sentiment_score  REAL,             -- optional parsed metric (-1..1)
  engagement_score REAL,             -- optional parsed metric (0..1)
  risk_score       REAL,             -- optional parsed metric (0..1)

  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  raw_json      TEXT                 -- store full response for debugging/replay
);

CREATE INDEX IF NOT EXISTS idx_gemini_outputs_session_role
  ON gemini_outputs(session_id, target_role);


-- ───────────────────────────────────────────────────────────
-- Mood timeseries (graph-friendly aggregates)
-- ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS mood_timeseries (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL REFERENCES sessions(session_id),

  subject_role    TEXT NOT NULL DEFAULT 'customer'
                  CHECK(subject_role IN ('customer','seller')),

  window_start_ms INTEGER NOT NULL,
  window_end_ms   INTEGER NOT NULL,

  mood_score      REAL,     -- typically avg(emotion_score) in that window
  engagement      REAL,     -- avg(engagement)
  blink_rate      REAL,     -- avg(blink_rate) if present
  is_talking_pct  REAL,     -- percent of samples where is_talking=1

  sample_count    INTEGER NOT NULL DEFAULT 0,
  source          TEXT NOT NULL DEFAULT 'presage',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mood_timeseries_session_time
  ON mood_timeseries(session_id, window_start_ms);

SELECT window_start_ms, mood_score, engagement
FROM mood_timeseries
WHERE session_id = ? AND subject_role = 'customer'
ORDER BY window_start_ms ASC;