# Events and audit stream

`app/events` defines typed domain/runtime events, the append-only event bus/store,
hash-chain audit verification, and the optional Spacetime projection seam. Events
are the causal record used by the UI WebSocket stream and audit views; they are not
permission to mutate state.

Important files include `schemas.py`, `bus.py`, `store.py`, `audit.py`, and
`spacetime.py`. Event sequence numbers and `since` cursors support ordered replay
and reconnect catch-up. The local smoke verifies that behavior.

Current Spacetime support is a seam/projection concept, not an externally verified
SpacetimeDB deployment. SQLite remains the authoritative local store.
