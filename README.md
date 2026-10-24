# Agentropolis

> Backend handoff: 77 tests and the repeatable local smoke pass. A separate chat is actively redesigning the frontend; current UI acceptance is pending. See [verification](docs/testing.md) and [final report](docs/implementation-report.md).
Agentropolis is a local autonomous business simulation with independent buyer and supplier agents. Watch companies request quotes, negotiate, reserve stock, receive goods, match invoices, settle payments, and recover from a supplier failure. The dashboard exposes the decisions, tasks, messages, approvals, and accounting behind each outcome.

The default demo needs no API keys. Banking, credit, demand, and fulfillment are simulated; economic state and agent work persist in SQLite. External adapters are opt-in and their verification status is disclosed in the [sponsor matrix](docs/sponsor-matrix.md). AgentPlace is not a runtime dependency.

## Run locally

Use Python 3.11 or later and a Node/npm installation compatible with the frontend lockfile. From this directory:

```sh
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[test]'
npm --prefix frontend ci
./scripts/dev.sh
```

Open [the economy dashboard](http://127.0.0.1:5173/economy/world). Vite prints the actual frontend port if 5173 is occupied. The backend uses port 8001; stop a previous Agentropolis instance before starting another. [API documentation](http://127.0.0.1:8001/docs) and [health](http://127.0.0.1:8001/health) are served by FastAPI. `Ctrl-C` stops the development launcher.

The seeded world starts paused. Use **Tick** for a controlled step or **Resume** to run the clock. The initial coffee contract has reserved stock and the equipment purchase is awaiting human approval. They are disclosed scenario inputs. New negotiations and replacement suppliers are selected from current business policies and independently issued quotes.

The default database directory is `backend/.data/sessions/`, one database per simulation. Restarting preserves state. The reset API creates a recoverable database checkpoint before reseeding a SQLite simulation. Reload the dashboard after a reset. See the [demo guide](docs/demo.md) for the repeatable presentation flow.

## Verify

With the virtual environment active:

```sh
(cd backend && python -m pytest -q)
npm --prefix frontend run build
npm --prefix frontend run lint
backend/scripts/demo_smoke.sh --full
```

The smoke script starts its own temporary in-memory API on an available port, exercises supplier failure and recovery twice, checks settlement and entity reconciliation, and verifies WebSocket catch-up. Browser tests need the development servers and Playwright Chromium; exact commands and recorded results are in [testing](docs/testing.md).

## What is implemented

- Eighteen role types share one runtime, with identities, registered permissions, tasks, private runtime memory, and durable messages. Core procurement roles exchange RFQs and counteroffers; operational roles perform concrete reviews and recommendations. See the [role matrix](docs/agent-architecture.md) for each role's limits.
- Economic commands validate business/session scope, stock, units, cost floors, committed cash, reserves, and approvals. Signing reserves stock; receipt creates AP/AR; a matched invoice can be paid and reconciled separately.
- SQLite transactions commit economic snapshots and their events together. Message delivery is at least once, with leases, retries, expiry, and idempotency at economic boundaries.
- World, business management/detail, negotiation, finance control tower, procurement, and scenario views expose the local simulation and audit trail. Human approval is available for purchases above the configured threshold.

This is a trusted local-operator demo. It has no authenticated multiuser authorization boundary, public Agentverse deployment, verified live sponsor settlement, or integrated x402 service-expense workflow. The [implementation report](docs/implementation-report.md) records remaining work; [external setup](docs/USER_SETUP_REQUIRED.md) lists access needed for credential-backed evidence.

## Guide

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, persistence, and execution boundaries |
| [Agent architecture](docs/agent-architecture.md) | All 18 roles, decisions, permissions, and transport |
| [Domain model](docs/domain-model.md) | Economic records, money, inventory, and state |
| [Workflows](docs/workflows.md) | Procurement, approvals, settlement, and recovery |
| [Security](docs/security.md) | Implemented controls and deployment limitations |
| [Design](DESIGN.md) | UI direction, editable artifacts, and visual evidence |
| [Testing](docs/testing.md) | Validation commands and evidence |
| [Demo](docs/demo.md) | Repeatable local demonstration |
| [Implementation report](docs/implementation-report.md) | Delivered scope and remaining acceptance work |

Source lives in `backend/app/` and `frontend/src/`; migrations are in `backend/migrations/`, seed inputs in `backend/scenarios/`, and deployment definitions in `infra/` plus `docker-compose.yml`. Docker definitions are supplied; use the testing report to distinguish provided configuration from verified execution.

## Architecture at a glance

```text
React/Vite dashboard
        │ HTTP projections + ordered WebSocket events
FastAPI API ── Agent orchestration ── business-owned role instances
        │                 │ typed proposals/messages
        └──── trusted EconomyEngine + Finance controls
                         │
              SQLite snapshots/events/runtime state
                         │
              optional, guarded provider adapters
```

Agents propose actions; trusted services validate and execute them. A purchase is
not a single animation: discovery and negotiation produce exact terms, treasury and
risk review them, the engine reserves stock, fulfillment produces a receipt, AP
matches the invoice, payment is authorized/submitted, and reconciliation closes the
record.

### The 18 roles

Manager/CEO, Procurement, Supplier/Sales, Negotiation, Inventory/Operations,
Strategy/Pricing, Treasury, Payments, Accounting, Accounts Payable, Accounts
Receivable, Risk/Compliance, Controller, Broker/Discovery, Market Intelligence,
Credit/Lending, Recovery, and Auditor/Observer share one durable runtime. See the
[role guide](docs/agent-architecture.md) for objectives, permissions and limits.

### Sponsor tracks

Hyphenate, Coinbase Payment Agents, Visa, Capital One Nessie, CRS Credit, Solana,
Fetch.ai, Creao, and SpacetimeDB each have an implementation guide in
[docs/tracks](docs/tracks/README.md). The local product and fixture statuses are
documented separately from credential-backed external verification; none should be
assumed eligible from the sponsor name alone.

### Repository guidance

- [AGENTS.md](AGENTS.md) — global coding-agent rules and safety boundary.
- [CLAUDE.md](CLAUDE.md) — Claude Code-specific operating rules.
- [Documentation index](docs/README.md) — architecture, workflows, testing,
  sponsor guides, and roadmap.
- [Final readiness](docs/final-readiness.md) — current evidence, frontend handoff
  gate, safe judging claims, and missing access.
- `python3 scripts/check_docs.py` — local Markdown-link/inventory validation.

Historical screenshots in `docs/evidence/` document an earlier UI snapshot. They do
not certify the active concurrent frontend redesign; use the final-readiness report
for the current acceptance boundary.
