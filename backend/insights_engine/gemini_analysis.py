import sqlite3
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Path to your SQLite DB (adjust as needed)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "adpitch.db")


def generate_call_summary(conversation, physiology_summary=None):
    prompt = f"""
You are an AI sales call analyst.

Provide a structured summary of this completed sales call.

Include:
- Overall summary (3-5 sentences)
- Key points (bullets)
- Action items for the agent
- Overall sentiment, engagement, and risk level

Conversation:
{conversation}
"""
    if physiology_summary:
        prompt += f"\nPhysiology Data:\n{physiology_summary}\n"

    response = model.generate_content(prompt)
    return response.text


def parse_gemini_response(text):
    # remove any code fences
    cleaned = text.replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback: just store raw text in summary_md
        return {
            "summary_md": cleaned,
            "key_points": "",
            "action_items": "",
            "sentiment_score": None,
            "engagement_score": None,
            "risk_score": None
        }


def save_gemini_output(session_id, ai_data, target_role="overall"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO gemini_outputs (
            session_id,
            target_role,
            summary_md,
            key_points,
            action_items,
            sentiment_score,
            engagement_score,
            risk_score,
            raw_json,
            model,
            model_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        target_role,
        ai_data.get("summary_md"),
        ai_data.get("key_points"),
        ai_data.get("action_items"),
        ai_data.get("sentiment_score"),
        ai_data.get("engagement_score"),
        ai_data.get("risk_score"),
        json.dumps(ai_data),
        "gemini",
        "1.5-flash"
    ))
    conn.commit()
    conn.close()


def run_ai_analysis(session_id, conversation, physiology_summary=None):
    raw = generate_call_summary(conversation, physiology_summary)
    ai_data = parse_gemini_response(raw)
    save_gemini_output(session_id, ai_data)
    return ai_data
