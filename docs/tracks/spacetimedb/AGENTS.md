# SpacetimeDB implementation-agent instructions

Mission: decide and implement a real-time projection or an explicitly bounded
authoritative subset without compromising financial consistency.

Own `backend/app/events/spacetime.py`, any provider module/schema, synchronization
tests, and this guide. Coordinate with events, database, API, frontend, and infra
owners before changing authority or transport.

Before code, document authority, consistency, ordering, replay, migration, and
failure semantics. Preserve event sequence/idempotency, session isolation, reset,
reconnect catch-up, and ledger authority. Run local WebSocket tests first, then
provider/module/reconnect/concurrency tests with disposable data.

Acceptance requires a deployed/tested SpacetimeDB path, two-client evidence, and
consistent authoritative records. Update matrix, setup, architecture, security,
and final readiness; report deployment and schema blockers.
