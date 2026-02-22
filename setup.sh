#!/usr/bin/env bash
# setup.sh — One-command setup for SenseLense backend
# Usage: bash setup.sh
# Works on macOS and Linux.

set -e  # exit on first error

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     SenseLense — Setup Script        ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Check Python ───────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌  python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓  Python $PY_VERSION found"

# ── 2. Create virtual environment ─────────────────────────────────────────────
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BACKEND_DIR/venv"

if [ ! -d "$VENV" ]; then
    echo "→  Creating virtual environment..."
    python3 -m venv "$VENV"
    echo "✓  venv created at $VENV"
else
    echo "✓  venv already exists"
fi

source "$VENV/bin/activate"

# ── 3. Upgrade pip ────────────────────────────────────────────────────────────
echo "→  Upgrading pip..."
pip install --quiet --upgrade pip

# ── 4. Install dependencies ───────────────────────────────────────────────────
echo "→  Installing Python dependencies (this may take a few minutes first time)..."
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
echo "✓  Dependencies installed"

# ── 5. Create .env if it doesn't exist ───────────────────────────────────────
ENV_FILE="$BACKEND_DIR/Transcriptions/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "→  Creating Transcriptions/.env from template..."
    cat > "$ENV_FILE" <<'EOF'
# Paste your API keys here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
PRESAGE_API_KEY=your_presage_key_here

# These are set automatically by Flask at runtime — you can leave them as-is
SESSION_ID=demo-session-001
ADPitch_DB=../instance/senselense.db
RECORD_SECONDS=900
EOF
    echo "⚠️   Created Transcriptions/.env — add your API keys before running!"
else
    echo "✓  Transcriptions/.env already exists"
fi

# ── 6. Initialize the database ───────────────────────────────────────────────
echo "→  Initializing database..."
cd "$BACKEND_DIR"
python3 -c "
from app import app
with app.app_context():
    from models import db
    db.create_all()
    print('✓  Database ready')
"

# ── 7. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Setup complete! ✅             ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "To start the backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  flask run"
echo ""
echo "Then open:  frontend/login.html  in your browser"
echo ""
