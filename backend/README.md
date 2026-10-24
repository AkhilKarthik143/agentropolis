# Agentropolis backend

The backend is a standalone FastAPI service that owns the authoritative local
economy. It hosts business-owned agent roles, the orchestration queue, the
deterministic economy engine, financial controls, SQLite event persistence, and
optional provider adapters.

## How it connects

`app/api` exposes HTTP and WebSocket projections. `app/orchestration` schedules
agents and persists tasks/messages. Agents propose typed procurement and review
actions. `app/economy` validates contracts, inventory, fulfillment and simulation
state; `app/finance` validates approvals, journals and reconciliation. Provider
clients under `app/integrations` are called only through explicit capabilities.

## Important files

- `app/main.py` — FastAPI application, CORS, lifecycle, health and WebSocket routes.
- `app/api/economy.py` — simulation API and runtime projection routes.
- `app/economy/engine.py` — trusted economic command boundary.
- `app/agents/registry.py` — role registration, message permissions and dispatch.
- `app/orchestration/store.py` and `app/events/store.py` — durable runtime/economic
  records and hash-chained events.
- `app/core/config.py` — standalone environment-backed settings.
- `migrations/` and `scenarios/seed_economy.json` — schema and reproducible seed.

## Run and test

From the repository root, install with `python -m pip install -e './backend[test]'`
inside an activated virtual environment, then run `./scripts/dev.sh`. Backend-only
verification is `(cd backend && PYTHONPATH=. python3 -m pytest -q)`. The isolated
demo proof is `bash backend/scripts/demo_smoke.sh --full`; it does not need the
frontend or provider credentials.

## Status and limits

The local implementation is verified with 77 tests and a repeatable supplier-shock
workflow. It is a trusted local-operator surface, not an authenticated multi-tenant
production service. External banking, public agent networking, and paid settlement
remain opt-in and separately evidenced.
