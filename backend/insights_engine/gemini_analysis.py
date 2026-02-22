import os
import sqlite3
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

# ─────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment.")

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
model = genai.GenerativeModel(MODEL_NAME)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "adpitch.db")

logging.basicConfig(level=logging.INFO)


# ─────────────────────────────────────────────────────────────
# Prompt Builders
# ─────────────────────────────────────────────────────────────

def _base_json_instruction() -> str:
    return """
Return ONLY valid JSON with this exact structure:

{
  "summary_md": string,
  "key_points": string,
  "action_items": string,
  "sentiment_score": number between -1 and 1,
  "engagement_score": number between 0 and 1,
  "risk_score": number between 0 and 1
}
Do not include markdown fences.
"""


def _build_overall_prompt(conversation: str, physiology_summary: Optional[str]) -> str:
    prompt = f"""
You are an AI sales call analyst.

Analyze this completed sales call.

Focus on:
- Overall performance
- Emotional dynamics
- Persuasion effectiveness
- Risk signals

Conversation:
{conversation}
"""
    if physiology_summary:
        prompt += f"\nPhysiology Signals:\n{physiology_summary}\n"

    prompt += _base_json_instruction()
    return prompt


def _build_seller_coaching_prompt(conversation: str) -> str:
    return f"""
You are an elite sales performance coach.

Analyze the SELLER only.

Focus on:
- Objection handling
- Framing
- Clarity
- Missed opportunities
- Closing technique
- Confidence signals

Conversation:
{conversation}

{_base_json_instruction()}
"""


def _build_customer_risk_prompt(conversation: str, physiology_summary: Optional[str]) -> str:
    prompt = f"""
You are a customer risk detection analyst.

Analyze the CUSTOMER.

Identify:
- Buying intent strength
- Emotional resistance
- Trust level
- Drop-off moments
- Churn likelihood

Conversation:
{conversation}
"""
    if physiology_summary:
        prompt += f"\nCustomer Physiology Signals:\n{physiology_summary}\n"

    prompt += _base_json_instruction()
    return prompt


# ─────────────────────────────────────────────────────────────
# Gemini Call
# ─────────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "top_p": 0.9,
                "max_output_tokens": 2048,
            }
        )
        return response.text.strip()
    except Exception as e:
        logging.exception("Gemini API call failed")
        raise RuntimeError(f"Gemini API error: {e}")


# ─────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────

def _safe_parse_json(text: str) -> Dict[str, Any]:
    cleaned = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logging.warning("Gemini did not return valid JSON. Storing raw text.")
        return {
            "summary_md": cleaned,
            "key_points": "",
            "action_items": "",
            "sentiment_score": None,
            "engagement_score": None,
            "risk_score": None,
        }


# ─────────────────────────────────────────────────────────────
# DB Storage
# ─────────────────────────────────────────────────────────────

def _save_gemini_output(
    session_id: str,
    ai_data: Dict[str, Any],
    target_role: str,
    raw_text: str,
):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")

        conn.execute(
            """
            INSERT INTO gemini_outputs(
              session_id, target_role, summary_md, key_points,
              action_items, sentiment_score, engagement_score,
              risk_score, raw_json, model, model_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                target_role,
                ai_data.get("summary_md"),
                ai_data.get("key_points"),
                ai_data.get("action_items"),
                ai_data.get("sentiment_score"),
                ai_data.get("engagement_score"),
                ai_data.get("risk_score"),
                json.dumps({"parsed": ai_data, "raw_text": raw_text}),
                "gemini",
                MODEL_NAME,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────

def run_ai_analysis(
    session_id: str,
    conversation: str,
    physiology_summary: Optional[str] = None,
) -> Dict[str, Any]:

    results = {}

    # 1️⃣ Overall
    overall_prompt = _build_overall_prompt(conversation, physiology_summary)
    overall_raw = _call_gemini(overall_prompt)
    overall_data = _safe_parse_json(overall_raw)
    _save_gemini_output(session_id, overall_data, "overall", overall_raw)
    results["overall"] = overall_data

    # 2️⃣ Seller Coaching
    seller_prompt = _build_seller_coaching_prompt(conversation)
    seller_raw = _call_gemini(seller_prompt)
    seller_data = _safe_parse_json(seller_raw)
    _save_gemini_output(session_id, seller_data, "seller", seller_raw)
    results["seller"] = seller_data

    # 3️⃣ Customer Risk
    customer_prompt = _build_customer_risk_prompt(conversation, physiology_summary)
    customer_raw = _call_gemini(customer_prompt)
    customer_data = _safe_parse_json(customer_raw)
    _save_gemini_output(session_id, customer_data, "customer", customer_raw)
    results["customer"] = customer_data

    return results
