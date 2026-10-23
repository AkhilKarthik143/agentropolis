# Extraction report

## Source and protection

Agentropolis was extracted from the Agentropolis-specific modules on the
`agentropolis-sponsors` branch. The source repository contained unrelated
uncommitted work; it was treated as read-only and was not reset, committed to,
or otherwise modified by this extraction.

## Moved into the standalone project

- Economy engine, contracts, state machine, inventory, scoring, clock, and scenarios.
- Event schemas, append-only bus, SQLite store, migrations, and audit chain.
- Finance controls, approvals, banking, ledger, reconciliation, and accounting.
- Agent gateway, structured LLM boundary, local transport, and role facades.
- Nessie, x402, Fetch, CRS, Apify, and SpacetimeDB adapter seams.
- Agentropolis-specific React pages, motion components, theme, event hooks, and API client.

## Refactored

- Imports now resolve through the standalone `app` package.
- FastAPI startup is `app.main:app`, not a shared server.
- Configuration uses `AGENTROPOLIS_*` variables for application-owned settings.
- Frontend routes contain only Agentropolis surfaces.
- Frontend proxy targets port 8001.
- SQLite migrations are checked into this repository.

## Deliberately not moved

AgentPlace customer/vendor pages, Supabase helpers, legacy negotiation routes,
legacy payment routes, legacy startup hooks, and AgentPlace database access were
not copied into the runtime.
