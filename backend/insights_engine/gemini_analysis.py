import google.generativeai as genai
import json
import re
import sqlite3
import os
from dotenv import load_dotenv

# Load .env for GEMINI_API_KEY
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Database path (adjust if needed)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database.db")


def generate_call_summary(conversation, physiology_summary=None):
    """
    Sends conversation (and optional physiology) to Gemini
    Returns raw text response
    """
    prompt = f"""
You are an AI sales call analyst.

Provide a structured summary of this completed sales call.

Include:
- Overall summary (3-5 sentences)
- Customer intent level (Low / Medium / High)
- Key objections
- Key buying signals
- Recommended improvement for the agent

Conversation:
{conversation}
"""
    if physiology_summary:
        prompt += f"\nPhysiology Data:\n{physiology_summary}\n"

    response = model.generate_content(prompt)
    return response.text


def parse_gemini_response(text):
    """
    Cleans text response and parses JSON
    """
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback if Gemini output is malformed
        return {
            "summary": cleaned,
            "intent_level": "Unknown",
            "objections": [],
            "buying_signals": [],
            "agent_improvement": ""
        }


def save_ai_summary(call_id, ai_data):
    """
    Saves structured AI summary to ai_summaries table
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ai_summaries (
            call_id,
            summary,
            intent_level,
            objections,
            buying_signals,
            agent_improvement
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        call_id,
        ai_data.get("summary"),
        ai_data.get("intent_level"),
        json.dumps(ai_data.get("objections", [])),
        json.dumps(ai_data.get("buying_signals", [])),
        ai_data.get("agent_improvement")
    ))
    conn.commit()
    conn.close()


def run_ai_analysis(call_id, conversation, physiology_summary=None):
    """
    Full pipeline: generate -> parse -> save
    """
    raw = generate_call_summary(conversation, physiology_summary)
    ai_data = parse_gemini_response(raw)
    save_ai_summary(call_id, ai_data)
    return ai_data  # optional: return for immediate use
