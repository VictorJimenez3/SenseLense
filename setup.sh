#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/backend"

if command -v uv >/dev/null 2>&1; then
    if [ ! -d venv ]; then
        uv venv venv --python 3.12
    fi
    uv pip install --python venv/bin/python -r requirements.txt
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3.10–3.12 is required. Install Python or uv, then retry." >&2
        exit 1
    fi
    if ! python3 -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)'; then
        echo "Python 3.10–3.12 is required; found $(python3 --version)." >&2
        exit 1
    fi
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
    venv/bin/pip install -r requirements.txt
fi

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created backend/.env; add your ElevenLabs and Gemini API keys."
fi

venv/bin/python -c "import app"

if [ "${1:-}" = "--seed" ]; then
    venv/bin/python seed.py
fi
