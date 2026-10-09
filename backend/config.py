"""Load backend environment variables and expose Flask configuration."""
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
    DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///senselense.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
