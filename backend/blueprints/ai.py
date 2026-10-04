import json
from typing import List, Dict, Any

from flask import Blueprint, current_app, jsonify, request
import google.generativeai as genai

from models import db, Session, Event

ai_bp = Blueprint("ai", __name__)

def compact_transcript(events: List[Event], max_chars: int = 25000) -> str:
    lines = []
    for e in events:
        if e.source == 'elevenlabs':
            text = (e.text or "").strip()
            if not text:
                continue
            lines.append(f"[{e.timestamp_ms}ms] {e.speaker or 'unknown'}: {text}")
    blob = "\n".join(lines)
    if len(blob) <= max_chars:
        return blob
    return blob[:max_chars]

def get_mood_data(events: List[Event]) -> List[Dict[str, Any]]:
    # Just extract a clean list of DeepFace events to pass to the prompt
    moods = []
    for e in events:
        if e.source == 'deepface' and e.emotion:
            moods.append({
                "t_ms": e.timestamp_ms,
                "emotion": e.emotion,
                "valence": e.valence
            })
    return moods

def generate_summary(session_id: int) -> Dict[str, Any]:
    session = Session.query.get_or_404(session_id)
    events = session.events
    
    transcript_text = compact_transcript(events)
    moods = get_mood_data(events)
    
    api_key = current_app.config["GEMINI_API_KEY"]
    if not api_key:
        return {"error": "Missing GEMINI_API_KEY"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(current_app.config["GEMINI_MODEL"])

    prompt = f"""
You are SenseLense AI, an expert sales analyst.
Return STRICT VALID JSON ONLY.

Schema:
{{
  "overall_summary": "string",
  "emotion_analysis": "string",
  "key_moments": [
    {{
      "t_ms": number,
      "description": "string",
      "emotion_context": "string"
    }}
  ],
  "risks": ["string"],
  "opportunities": ["string"],
  "next_steps": ["string"],
  "confidence": number
}}

Transcript:
{transcript_text}

Emotion Data (ms, emotion, valence -1 to 1):
{json.dumps(moods)}
"""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except Exception as e:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                parsed = json.loads(raw[start:end+1])
            except:
                raise RuntimeError(f"JSON Parse Error: {e}")
        else:
            raise RuntimeError(f"Gemini returned invalid JSON")

    return parsed

@ai_bp.post("/sessions/<int:session_id>/summary/generate")
def generate_endpoint(session_id: int):
    try:
        summary_data = generate_summary(session_id)
        if "error" in summary_data:
            return jsonify({"ok": False, "error": summary_data["error"]}), 500
            
        session = Session.query.get(session_id)
        if session:
            # Build an attractive markdown summary to display on the frontend
            summary_md = ""
            if session.summary and session.summary != "Session completed.":
                summary_md += f"**User Notes**\n{session.summary}\n\n---\n\n"
            
            summary_md += f"**Overall Analysis**\n{summary_data.get('overall_summary', '')}\n\n"
            summary_md += f"**Emotional Context**\n{summary_data.get('emotion_analysis', '')}\n\n"
            
            risks = summary_data.get('risks', [])
            if risks:
                summary_md += "**Risks**\n" + "\n".join(f"- {r}" for r in risks) + "\n\n"
                
            opps = summary_data.get('opportunities', [])
            if opps:
                summary_md += "**Opportunities**\n" + "\n".join(f"- {o}" for o in opps) + "\n\n"
                
            steps = summary_data.get('next_steps', [])
            if steps:
                summary_md += "**Next Steps**\n" + "\n".join(f"- {s}" for s in steps) + "\n"
                
            session.summary = summary_md.strip()
            db.session.commit()
            
        return jsonify({"ok": True, "summary_md": session.summary, "raw_data": summary_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500
