#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_PYTHON="${TASK_ROOT}/.venv/bin/python"
if [ ! -x "$TASK_PYTHON" ]; then TASK_PYTHON=python3; fi
cleanup() { kill "${API_PID:-}" "${UI_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd "$TASK_ROOT/backend"; "$TASK_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8001) &
API_PID=$!
(cd "$TASK_ROOT/frontend"; npm run dev -- --host 127.0.0.1) &
UI_PID=$!
printf 'Agentropolis: backend http://127.0.0.1:8001 · frontend shown by Vite below\n'
wait
