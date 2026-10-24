# Hyphenate implementation-agent instructions

Mission: maintain the local autonomous-finance workflow and add only official
Hyphenate capabilities that are confirmed by the event brief.

Own `backend/app/finance/`, finance role branches in
`backend/app/agents/financial_operations.py`, finance/economic tests, and this
guide. Coordinate changes to `app/economy/engine.py`, API projections, and frontend
views before editing them.

Preserve integer cents, independent entity balance, approval-before-payment,
invoice/receipt matching, idempotency, uncertainty, and reconciliation. Use typed
provider contracts; do not make an agent call an external API directly.

Run ledger, reconciliation, integrity, approval, and full backend tests. Acceptance
requires a local end-to-end trace plus any real Hyphenate evidence required by the
official rules. Do not invent an API. Update `docs/sponsor-matrix.md`,
`docs/final-readiness.md`, and `docs/USER_SETUP_REQUIRED.md` with status and
credentials. Report changed files, invariant tests, provider evidence, and blockers.
