#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

(
    cd "$ROOT_DIR/backend"
    exec venv/bin/python -m flask run --debug
) &
BACKEND_PID=$!

(
    cd "$ROOT_DIR/frontend"
    exec python3 -m http.server 8080
) &
FRONTEND_PID=$!

cleanup() {
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM
echo "SenseLense is running at http://localhost:8080/"
wait
