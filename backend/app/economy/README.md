# Economy engine

The economy layer is the authoritative simulation state machine. It models
businesses, products, offers, contracts, inventory, clock/shocks, fulfillment,
pricing, scoring, and trusted commands. Agents can propose a purchase, but the
engine validates stock, price/cost floor, cash commitments, approval, legal
transition, session scope, and idempotency before changing state.

Key files are `engine.py`, `contracts.py`, `inventory.py`, `state_machine.py`,
`clock.py`, `scenarios.py`, `pricing.py`, `scoring.py`, and `persistence.py`.
Supplier failure/recovery is exercised by `backend/scripts/demo_smoke.sh --full`.

## Invariants

- Money is represented in integer cents.
- Inventory is reserved before a contract is accepted and cannot be oversold.
- Signing, shipping, receipt, invoice match, payment, and reconciliation are
  separate transitions.
- Simulations and businesses cannot act across one another's scope.
- Repeated commands are idempotent and every public transition has an event trace.

The default world is deterministic/local. It is not a claim of physical fulfillment,
bank settlement, or live market data.
