# API layer

`backend/app/api/economy.py` is the current public application surface. It exposes
the seeded/default economy routes, simulation-scoped business/agent/contract,
scenario, approval, finance and event projections, plus WebSocket streams for
ordered event delivery and reset/reconnect behavior.

## Workflow

HTTP commands request a state transition from the selected runtime; the engine
validates business, session, policy, inventory and financial conditions. Responses
are projections, not permission to bypass the engine. WebSockets stream persisted
events with a `since` cursor so a client can reconnect and catch up.

Important paths include `app/api/economy.py`, `app/main.py`, and API guard tests in
`backend/tests/test_api_guards.py`. Start the service with `./scripts/dev.sh`; the
API is normally `http://127.0.0.1:8001` and OpenAPI is `/docs`.

## Status

The simulation routes and reset/reconnect behavior are locally tested. The API is
not authenticated for public multiuser deployment. Do not add provider credentials
or financial authority to a route without a corresponding server-side capability,
audit event, and test.
