import os, json, time, sys
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from recordings.audio import record_wav

# NEW: DB helpers (create transcription/db_writer.py from earlier message)
# Add repo root to Python path so "sync_engine" imports work
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)
from database.db_manager import (
    insert_session,
    insert_transcript_segments,
    upsert_speaker_map,
    apply_speaker_map_to_segments, compute_and_write_mood_timeseries, insert_gemini_output
)

def to_ms(seconds: float) -> int:
    return int(round(float(seconds) * 1000))


def main():
    load_dotenv()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    session_id = os.getenv("SESSION_ID", "demo-session")
    out_file = os.getenv("OUT_FILE", "segments.jsonl")
    db_path = os.getenv("ADPitch_DB")  # ../sync-engine/data/adpitch.db
    record_seconds = int(os.getenv("RECORD_SECONDS", "900"))  # 15 min default

    if not api_key:
        raise SystemExit("Missing ELEVENLABS_API_KEY in transcription/.env")
    if not db_path:
        raise SystemExit("Missing ADPitch_DB in transcription/.env (example: ../sync-engine/data/adpitch.db)")

    # 1) Insert session row (the glue)
    started_at_epoch_ms = int(time.time() * 1000)
    import sqlite3, os

    print("[debug] using db_path:", db_path, "abs:", os.path.abspath(db_path))
    conn = sqlite3.connect(db_path)
    print("[debug] tables:", conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall())
    conn.close()
    insert_session(db_path, session_id, started_at_epoch_ms)

    # 2) Record audio (WAV)
    wav_path = "call.wav"
    record_wav(wav_path, seconds=record_seconds, sample_rate=16000, channels=1)

    # 3) STT (Batch) with diarization
    client = ElevenLabs(api_key=api_key)
    print("[stt] Sending audio to ElevenLabs (scribe_v2, diarize=True)...")
    with open(wav_path, "rb") as f:
        result = client.speech_to_text.convert(
            file=f,
            model_id="scribe_v2",
            diarize=True,
        )

    segments = getattr(result, "segments", None) or (result.get("segments") if isinstance(result, dict) else None)

    # 4) Build rows
    segments_out = []
    if segments:
        for seg in segments:
            speaker_label = getattr(seg, "speaker", None) or (seg.get("speaker") if isinstance(seg, dict) else "unknown")
            text = getattr(seg, "text", None) or (seg.get("text") if isinstance(seg, dict) else "")
            start_s = getattr(seg, "start", None) or (seg.get("start") if isinstance(seg, dict) else 0.0)
            end_s = getattr(seg, "end", None) or (seg.get("end") if isinstance(seg, dict) else start_s)

            row = {
                "session_id": session_id,
                "speaker_label": speaker_label,
                "text": (text or "").strip(),
                "start_ms": to_ms(start_s),
                "end_ms": to_ms(end_s),
            }
            # skip empty text rows
            if row["text"]:
                segments_out.append(row)
    else:
        # fallback: whole transcript as one segment
        text = getattr(result, "text", None) or (result.get("text") if isinstance(result, dict) else "")
        segments_out = [{
            "session_id": session_id,
            "speaker_label": "unknown",
            "text": str(text).strip(),
            "start_ms": 0,
            "end_ms": 0,
        }]

    # 5) Write jsonl file (handy for debugging / demo)
    with open(out_file, "w", encoding="utf-8") as w:
        for row in segments_out:
            w.write(json.dumps({
                "session_id": row["session_id"],
                "speaker": row["speaker_label"],
                "text": row["text"],
                "start_ms": row["start_ms"],
                "end_ms": row["end_ms"],
            }, ensure_ascii=False) + "\n")

    print(f"[file] Wrote {len(segments_out)} segments to {out_file}")

    print("[debug] using db_path:", db_path)
    # 6) Insert into DB
    insert_transcript_segments(db_path, segments_out)
    print(f"[db] Inserted {len(segments_out)} rows into transcript_segments")

    # 7) Map diarized labels to seller/client (hackathon heuristic)
    # First seen label = seller, second = client
    seen = []
    for r in segments_out:
        lab = r["speaker_label"]
        if lab != "unknown" and lab not in seen:
            seen.append(lab)
        if len(seen) >= 2:
            break

    if len(seen) >= 2:
        seller_label, client_label = seen[0], seen[1]
        upsert_speaker_map(db_path, session_id, seller_label=seller_label, client_label=client_label)
        print(f"[map] seller={seller_label} client={client_label} (speaker_map + transcript_segments updated)")
    else:
        print("[map] Not enough distinct speakers found to map seller/client (ok for now)")
    if len(seen) >= 2:
        seller_label, client_label = seen[0], seen[1]
        upsert_speaker_map(db_path, session_id, seller_label=seller_label, client_label=client_label)
        apply_speaker_map_to_segments(db_path, session_id)
        print(f"[map] seller={seller_label} client={client_label} (speaker_map + transcript_segments.speaker updated)")
    else:
        print("[map] Not enough distinct speakers found to map seller/customer (ok for now)")
    print("[done] transcription -> db complete")


    n = compute_and_write_mood_timeseries(db_path, session_id, window_ms=10_000)
    print("[ts] wrote:", n)

    # Placeholder values for Gemini integration (to be replaced by actual analysis)
    customer_summary_md = "Session summary pending AI analysis."
    gemini_resp = "{}"

    insert_gemini_output(
        db_path, session_id,
        target_role="customer",
        summary_md=customer_summary_md,
        raw_json=gemini_resp,
    )
if __name__ == "__main__":
    main()