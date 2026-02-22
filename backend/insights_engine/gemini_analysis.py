import google.generativeai as genai
import json
import re
from shared.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def generate_call_summary(conversation, physiology_summary=None):

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
