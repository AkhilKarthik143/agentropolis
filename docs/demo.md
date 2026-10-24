# Repeatable local demo

> Handoff note: the user confirmed a concurrent UI redesign on October 23. Descriptions and screenshots below document the earlier verified UI snapshot; recheck against the final UI chat output. See docs/testing.md (testing.md from within docs).
No external key or real money is required. Follow README installation, then run `./scripts/dev.sh` from the repository. Backend: http://127.0.0.1:8001; Vite prints its selected frontend port. The checked session used http://127.0.0.1:5176/economy/world. Do not run against another project's server.

## Automated proof

From the repository: `bash backend/scripts/demo_smoke.sh --full`. It selects a free loopback port, starts an isolated in-memory backend, verifies reset + supplier recovery twice, checks receipt/single settlement/reconciliation and verifies ordered WebSocket catch-up. It stops its own server on exit. `--full` is retained as a compatible invocation; the script always runs the complete local smoke.

## Three-minute presentation

0:00–0:30 — Open World. Say: “This is a local simulated economy. Companies own separate agents; deterministic services enforce money and inventory.” Show ten companies and the local transport/bank disclosure. Inspect one company's team.

0:30–1:10 — Advance one tick. Harbor Foods finds competing packaging offers; supplier quotes are calculated independently and countered. Open Negotiations, select the packaging contract and inspect its quotes and public rationale. Show the equipment purchase still waiting for human approval.

1:10–1:45 — Advance the clock until receipt/payment. Open Control tower: show PO, receipt, invoice, match, separate fulfillment/payment states, buyer/seller journals and reconciliation. “Contract accepted” is not “paid.”

1:45–2:35 — For a clean crisis story reset first, then choose Northstar supplier bankruptcy in Shock engine. It defaults the pending coffee contract. Advance four ticks. Recovery negotiates with current available suppliers; open the replacement coffee contract, then show its received/reconciled state. The selected supplier can depend on objectives and available stock.

2:35–3:00 — Inspect the audit/event trace and mention the safeguards: reserve, exact-term approval, matched invoice, duplicate protection and distinct uncertain-payment handling. Disclose external integrations accurately using sponsor-matrix.md.

## Reset before rehearsal

`curl -X POST http://127.0.0.1:8001/api/simulations/demo_001/reset`

Reset is restricted to the mock bank. SQLite mode creates a database checkpoint under the configured data directory. Refresh the browser if needed. The smoke script uses its own memory session and does not reset a running demo.

## Evidence and backup

Actual screenshots: `evidence/world-desktop.png`, `world-small-laptop.png`, `world-mobile.png`, `negotiations-desktop.png`, `finance-desktop.png` and laptop counterparts. Automated tests create a clearly named Browser QA company; screenshots may show eleven businesses for this reason. Open local screenshots as a static backup. No narrated backup video or public deployment was produced.

Public Fetch/Agentverse, live banking and testnet x402 are separate demonstrations and must not be claimed from this local demo. There is no completed end-to-end paid digital research-service journey yet.
