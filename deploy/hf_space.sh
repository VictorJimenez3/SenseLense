#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: bash deploy/hf_space.sh <hf-username> [space-name=senselense-backend]" >&2
    exit 2
fi

HF_USERNAME="$1"
SPACE_NAME="${2:-senselense-backend}"

if ! command -v hf >/dev/null 2>&1; then
    echo "hf CLI not found on PATH." >&2
    exit 1
fi

if ! hf auth whoami >/dev/null 2>&1; then
    echo "Not logged in to Hugging Face; run: hf auth login" >&2
    exit 1
fi

hf repos create "$HF_USERNAME/$SPACE_NAME" --type space --sdk docker --exist-ok

STAGE="$(mktemp -d)"
trap 'rm -rf -- "$STAGE"' EXIT

rsync -a \
    --exclude='venv/' \
    --exclude='instance/' \
    --exclude='__pycache__/' \
    --exclude='.pytest_cache/' \
    --exclude='.env' \
    --exclude='tests/' \
    backend/ "$STAGE/"

cat > "$STAGE/README.md" <<'EOF'
---
title: SenseLense Backend
emoji: 🎯
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
Flask API for SenseLense. Set ELEVENLABS_API_KEY and GEMINI_API_KEY as Space secrets.
EOF

hf upload "$HF_USERNAME/$SPACE_NAME" "$STAGE" . --repo-type space

SLUG_USER="$(printf '%s' "$HF_USERNAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
SLUG_SPACE="$(printf '%s' "$SPACE_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
echo "Space URL: https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"
echo "API base: https://$SLUG_USER-$SLUG_SPACE.hf.space (HF lowercases and replaces underscores with hyphens)"
echo "Add ELEVENLABS_API_KEY and GEMINI_API_KEY in Space settings → Variables and secrets."
echo "Then check: curl https://$SLUG_USER-$SLUG_SPACE.hf.space/api/health"
