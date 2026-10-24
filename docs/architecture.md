# Architecture

Agentropolis runs a React/Vite client and a standalone FastAPI service. One local service process hosts multiple business teams and simulation sessions. Agent decisions are separated from the trusted code that mutates contracts, inventory, banking, and accounting.

```text
React dashboard ── HTTP commands / snapshots ──► FastAPI
      ▲                                           │
      └──── WebSocket events + reconnect cursor ───┤
                                                  ▼
                                      Simulation clock / scheduler
                                                  │
                               ┌──────────────────┴─────────────────┐
                               ▼                                    ▼
                       Buyer-owned teams                  Supplier-owned agents
                               └──── durable RFQs / counteroffers ──┘
                                                  │ proposals
                                                  ▼
                                       EconomyEngine command gate
                                   policy · stock · approval · invoice
                                                  │
                              ┌───────────────────┴──────────────────┐
                              ▼                                      ▼
                    Local bank + ledger                    Contract + inventory
                              └───────────────────┬──────────────────┘
                                                  ▼
                              SQLite economic snapshot + event chain
```

## Component boundaries

| Component | Responsibility |
| --- | --- |
| `frontend/src` | Live projections, business controls, negotiation history, finance, and audit views; no authority to settle money |
| `app/api/economy.py` | Compatibility routes for the default world and session-scoped routes; local scheduler and WebSocket streams |
| `app/orchestration/runtime.py` | Registers business teams, advances policy work, dispatches messages, and invokes due simulated fulfillment/payment commands |
| `app/agents` | Scoped identities and policies; buyer tasks and negotiation are separate from supplier quote decisions |
| `app/orchestration/store.py` | Durable inbox, leases, tasks, negotiation state, agent counters, and memory |
| `app/economy/engine.py` | Validates and executes economic mutations; agents cannot bypass its validations through the normal workflow |
| `app/finance` | Integer-cent journals, approvals, PO/receipt/invoice match, mock banking, and reconciliation |
| `app/events` | Ordered, hash-chained events, persisted snapshots, replay, and bounded local fan-out |
| `app/integrations` | Optional provider adapters; the default economy remains local |

No runtime code depends on an AgentPlace server, database, checkout, or environment file. The project loads its own root `.env`.

## Persistence and concurrency

SQLite is the default. Each session uses `backend/.data/sessions/<simulation_id>.db`, or the equivalent path below `AGENTROPOLIS_DATA_DIR`. Session IDs are constrained to a safe filename alphabet. Migrations create the event log, versioned economic snapshot, and agent runtime tables. `AGENTROPOLIS_STORE=memory` is useful for isolated tests and intentionally loses state on exit.

An economic command acquires the engine lock and a SQLite `BEGIN IMMEDIATE` transaction, refreshes newer committed state, validates, mutates, and saves its JSON snapshot with its events. An exception rolls back both records and in-memory economic state. Event subscribers are notified after commit. The snapshot includes business/inventory state, contracts, payments, ledger, finance controls, mock bank history, approvals, idempotent outcomes, clock, and faults.

The agent queue uses separate transactions on the same database. Claims have expiring leases; retries and private policy state survive restart. Queue acknowledgement and economic mutation are **not one distributed transaction**. Delivery is at least once, with stable workflow keys and idempotent economic commands preventing a repeated message from paying twice. See [agent architecture](agent-architecture.md) for exact retry semantics.

The supported deployment is a single application worker. SQLite tests cover competing economic commands, but the scheduler and WebSocket fan-out remain process-local. Multiple Uvicorn workers are not a supported distributed orchestration deployment. The scheduler tracks a separate next-tick deadline and speed for each active session.

## Reads and streams

`GET /api/simulations/{id}` returns the economic summary plus runtime projections. `/api/economy/*` addresses `demo_001` for compatibility. `GET .../events?since=N` and `/ws/simulations/{id}?since=N` use increasing event sequence numbers. WebSockets send heartbeats and a resync signal when a bounded subscriber queue cannot retain the full backlog. The UI can reload a summary and catch up by cursor. A simulation reset sends a resync signal and closes the retired stream so clients can reconnect from sequence zero.

The event chain is an audit aid. Restart restores the durable snapshot; the current replay endpoint reports retained history rather than rebuilding arbitrary historical snapshots from an event reducer. Hashes are not externally anchored and do not prevent a database administrator from rewriting the database and recomputing the chain.

## Integrations and operating limits

The default bank and credit service are simulated. Local uAgents dispatch has been exercised separately; the economy's authoritative transport remains its durable local queue. Claude reasoning, Nessie banking, public Agentverse, Apify, and x402 require additional configuration and external evidence. Merely setting an adapter variable does not switch economic settlement to that provider. See [sponsor status](sponsor-matrix.md).

The API trusts the local operator and is bound to loopback by the development and Docker configuration. There is no user authentication, tenant authorization, production secret store, or public-service abuse protection. Internal role checks and session separation protect workflow correctness; they are not a multiuser security boundary. See [security](security.md).
