# Visa implementation-agent instructions

Mission: improve autonomous shopping and add a Visa-specific integration only when
the official challenge contract requires and supports it.

Own procurement/broker/scoring tests and the track guide. Coordinate with the
agents/economy owners for supplier and contract changes and with the frontend owner
for marketplace UI changes.

Preserve independent supplier state, transparent score inputs, buyer policy,
budget/reserve checks, human approval, expiration, inventory reservation, and
auditability. Never select a supplier from hidden or invented data, and never call
an external payment endpoint from React.

Run procurement, engine, scenario, role, and full backend tests plus current UI
acceptance after frontend handoff. Acceptance is a local shopping trace first and
a Visa external claim only after actual provider evidence. Update matrix, setup,
and final readiness; report the exact challenge requirement still blocking work.
