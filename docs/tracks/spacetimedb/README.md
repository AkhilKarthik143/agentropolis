# SpacetimeDB — real-time synchronization

## Goal and authority model

SpacetimeDB could provide multi-client live state, negotiation updates, task status,
and economic activity. It must be a projection of the authoritative SQLite/event
store unless a separately reviewed migration makes it authoritative for a defined
subset. Two stores must never independently write financial balances.

## Current architecture

The repository has `backend/app/events/spacetime.py` as a seam and a tested local
WebSocket event stream with ordering, cursor catch-up, reset, and session
isolation. `SPACETIMEDB_URI` and `SPACETIMEDB_DATABASE` are placeholders; no
SpacetimeDB deployment or subscription is verified.

## Missing and test/demo plan

Missing are the authority decision, module/schema, client subscription, provider
deployment, reconnect/dedup/order tests, and multi-browser evidence. A future demo
must show two clients observing the same negotiation/shock while SQLite/ledger
remains consistent. Current local smoke is not SpacetimeDB evidence.

## Definition of done

SpacetimeDB materially supplies tested synchronization with a documented consistency
model, restart/reconnect behavior, and a real multi-client demo. An unused client or
placeholder URI does not qualify.
