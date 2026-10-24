#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "preflight: Python executable not found: $PYTHON_BIN" >&2
  exit 2
fi

echo "== Agentropolis local preflight =="
echo "project: $PROJECT_ROOT"
echo "python:  $($PYTHON_BIN --version 2>&1)"

if git ls-files | rg -q '(^|/)\.env$'; then
  echo "preflight: tracked .env file found; remove it before sharing the repository" >&2
  exit 1
fi
echo "secrets: no tracked .env file"

echo "-- backend tests --"
(cd backend && PYTHONPATH=. "$PYTHON_BIN" -m pytest -q)

echo "-- isolated local demo smoke --"
bash backend/scripts/demo_smoke.sh --full

echo "-- local Fetch/uAgents exchange --"
(cd backend && PYTHONPATH=. "$PYTHON_BIN" scripts/verify_fetch.py)

echo "-- external evidence gates --"
echo "Nessie: skipped; set NESSIE_MODE=sandbox and NESSIE_API_KEY, then run backend/scripts/verify_nessie.py"
echo "x402:   skipped; configure approved Base Sepolia test resources, then run backend/scripts/verify_x402.py"
echo "Claude:  skipped; configure an explicitly approved Anthropic key, then run the live gateway check"

echo "preflight: local release checks passed; external sponsor verification remains pending"
