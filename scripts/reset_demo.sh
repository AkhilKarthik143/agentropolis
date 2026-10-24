#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${AGENTROPOLIS_BASE_URL:-http://127.0.0.1:8001}"

case "$BASE_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *)
    echo "reset_demo: refusing non-loopback URL: $BASE_URL" >&2
    echo "Set AGENTROPOLIS_BASE_URL to a local Agentropolis server only." >&2
    exit 2
    ;;
esac

echo "Resetting local Agentropolis demo at $BASE_URL"
curl --fail-with-body --silent --show-error \
  -X POST \
  "$BASE_URL/api/simulations/demo_001/reset"
echo
echo "Demo reset complete. Reload the dashboard before rehearsing."
