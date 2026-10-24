#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TASK_PYTHON="${ROOT_DIR}/.venv/bin/python"
if [ ! -x "$TASK_PYTHON" ]; then TASK_PYTHON=python3; fi
PORT="${AGENTROPOLIS_SMOKE_PORT:-$("$TASK_PYTHON" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')}"
LOG_FILE="$(mktemp -t agentropolis-smoke)"
cleanup() { if [ -n "${SERVER_PID:-}" ]; then kill "$SERVER_PID" >/dev/null 2>&1 || true; wait "$SERVER_PID" >/dev/null 2>&1 || true; fi; rm -f "$LOG_FILE"; }
trap cleanup EXIT
(cd "$ROOT_DIR/backend"; AGENTROPOLIS_STORE=memory "$TASK_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT") >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
"$TASK_PYTHON" - "$PORT" <<'PY'
import asyncio,json,sys,time,urllib.request
import websockets
base=f'http://127.0.0.1:{sys.argv[1]}'
def call(path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
for _ in range(40):
    try:call('/health');break
    except OSError:time.sleep(.2)
else:raise SystemExit('backend did not start')
root='/api/simulations/demo_001'
for attempt in range(2):
    if attempt:call(root+'/reset',{})
    initial=call(root)
    assert len(initial['businesses'])>=10 and len(initial['ledger'])>0
    assert not initial['finance']['receipts']
    call(root+'/shock',{'type':'supplier_bankruptcy','supplier_id':'northstar_roasters'})
    for _ in range(4):call(root+'/tick',{})
    result=call(root)
    replacements=[c for c in result['contracts'] if c['recovery']]
    assert replacements and all(c['fulfillment_state']=='RECEIVED' and c['payment_state']=='RECONCILED' for c in replacements)
    assert all(r['ok'] for r in result['reconciliation'])
    assert result['ledger_proof']['balanced'] and result['audit']['valid']
    types={event['type'] for event in call(root+'/events')}
    assert {'RequestForQuote','RFQSent'}&types
    assert {'SupplierDefaulted','RecoveryPlanProposed','OfferReceived','SupplierCounterOffer','ContractAccepted','InventoryReceiptConfirmed','PaymentConfirmed','Reconciled'}<=types
    print(f'repeat {attempt+1}: independent negotiation, replacement receipt, single settlement, reconciled entities')
async def stream():
    events=call(root+'/events');since=events[-2]['seq']
    async with websockets.connect(f'ws://127.0.0.1:{sys.argv[1]}/ws/simulations/demo_001?since={since}') as ws:
        event=json.loads(await asyncio.wait_for(ws.recv(),5));assert event['seq']>since
    print('WebSocket reconnect: ordered catch-up verified')
asyncio.run(stream())
print('Local simulation smoke passed; no external sponsor settlement claimed.')
PY
