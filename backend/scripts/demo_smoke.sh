#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${AGENTROPOLIS_SMOKE_PORT:-8098}"
FULL_MODE="${1:-}"
LOG_FILE="$(mktemp -t agentropolis-smoke).log"
cleanup() {
  if [ -n "${SERVER_PID:-}" ]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$LOG_FILE"
}
trap cleanup EXIT

(
  cd "$ROOT_DIR/backend"
  AGENTROPOLIS_STORE=memory python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
) >"$LOG_FILE" 2>&1 &
SERVER_PID=$!

python3 - "$PORT" "$FULL_MODE" <<'PY'
import json, sys, time, urllib.request
port = sys.argv[1]
full = sys.argv[2] == "--full"
url = f"http://127.0.0.1:{port}"
for _ in range(40):
    try:
        urllib.request.urlopen(url + "/api/health", timeout=1).read()
        break
    except Exception:
        time.sleep(.2)
else:
    raise SystemExit("backend did not become ready")

def get(path):
    with urllib.request.urlopen(url + path, timeout=2) as response:
        return json.load(response)

def post(path, payload):
    req = urllib.request.Request(url + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=2) as response:
        return json.load(response)

before = get("/api/simulations/demo_001")
assert len(before["businesses"]) >= 5
assert len(before["approvals"]) >= 1
post("/api/simulations/demo_001/start", {})
if full:
    approval = next(item for item in before["approvals"] if item["status"] == "pending")
    post(f"/api/simulations/demo_001/approvals/{approval['approval_id']}", {"approved": True, "approver": "human_operator"})
post("/api/simulations/demo_001/shock", {"type": "SUPPLIER_BANKRUPTCY", "supplier_id": "northstar_roasters"})
after = get("/api/simulations/demo_001")
all_events = get("/api/simulations/demo_001/events?since=0")
event_types = {event["type"] for event in all_events}
assert {"ShockInjected", "SupplierDefaulted", "ReplanStarted", "ContractAccepted"}.issubset(event_types), event_types
assert {"SUPPLIER_BANKRUPT", "DELIVERY_AT_RISK", "RECOVERY_STARTED", "REPLACEMENT_APPROVED", "INVENTORY_RECOVERED"}.issubset(event_types), event_types
assert {"CRS_CHECKED", "SUPPLIER_BLOCKED", "ACTION_BLOCKED"}.issubset(event_types), event_types
assert get("/api/simulations/demo_001/ledger/proof")["balanced"] is True
assert get("/api/simulations/demo_001/audit/verify")["valid"] is True
if full:
    assert "ApprovalGranted" in event_types, event_types
assert sum(after["trial_balance"].values()) == 0
buyer = next(item for item in after["businesses"] if item["role"] == "buyer")
assert buyer["cash_cents"] >= buyer["reserve_cents"] or any(item["status"] == "pending" for item in after["approvals"])
print("mock smoke passed: CRS block, recovery contract, balanced ledger, audit proof, reserve policy")
if full:
    print("full sponsor smoke passed: human approval and blocked injection")
PY

python3 - "$PORT" <<'PY'
import asyncio, json, sys
import websockets

async def main():
    seen = set()
    async with websockets.connect(f"ws://127.0.0.1:{sys.argv[1]}/ws/simulations/demo_001?since=0") as ws:
        for _ in range(100):
            item = json.loads(await ws.recv())
            if item.get("type") != "heartbeat":
                seen.add(item.get("type"))
            if {"ShockInjected", "ReplanStarted", "LedgerPosted"}.issubset(seen):
                break
    assert "ShockInjected" in seen and "ReplanStarted" in seen, seen
    print("websocket smoke passed: ordered backfill received")

asyncio.run(main())
PY

if [ "$FULL_MODE" = "--full" ]; then
  PYTHONPATH="$ROOT_DIR/backend" python3 "$ROOT_DIR/backend/scripts/asi_local_client.py" "Run the purchase and recover if Northstar goes bankrupt." >/dev/null
  echo "gateway smoke passed: offline Chat Protocol-shaped purchase and recovery"
fi
