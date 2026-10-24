# Economy coding-agent instructions

Treat `EconomyEngine` as a trusted command boundary. Add legal transitions to
`state_machine.py`, validate all preconditions before mutation, emit one
idempotent event per effect, and keep snapshot/event writes atomic.

Never let an LLM, HTTP adapter, frontend payload, or agent message write balances,
stock, contracts, or payment state directly. Preserve independent supplier quotes,
reservation accounting, exact approved terms, partial receipt behavior, uncertainty
states, and reset/reconnect semantics.

Run focused engine/state/scenario/integrity tests, then
`bash backend/scripts/demo_smoke.sh --full`. Add a regression test for every new
invariant or legal transition. Report seed/schema compatibility and demo impact.
