"""Vercel entrypoint for the SenseLense Flask API.

The production project keeps the application in ``backend/``. Vercel's
Python runtime imports a module under ``api/``, so this small adapter adds the
backend directory to ``sys.path`` and exposes the existing Flask app.
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Vercel's filesystem is ephemeral. /tmp is writable for the lifetime of a
# function instance and lets the existing SQLite-backed CRUD API start safely.
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/senselense.db")

from app import app  # noqa: E402

