# Backend agent instructions

## Responsibility

Maintain the FastAPI service, durable agent runtime, economy, finance, persistence,
and provider adapters without weakening economic invariants.

## Scope

Read the nearest child instructions before editing `app/api`, `app/agents`,
`app/economy`, `app/finance`, `app/integrations`, `app/orchestration`, `app/database`,
`app/events`, or `app/security`. Coordinate before changing frontend files or shared
API shapes consumed by the active frontend redesign.

## Required invariants

- Agents cannot impersonate another business/role or grant their own authority.
- Commands are scoped to a simulation and business.
- Inventory is reserved before acceptance and cannot be oversold.
- Receipt, invoice match, payment authorization, provider submission, and
  reconciliation remain distinct states.
- Every legal-entity journal balances; uncertain provider outcomes are retained and
  never blindly retried.
- Durable retries and duplicate messages do not duplicate economic effects.

## Tests and report

Run focused tests for the changed subsystem, then the full backend suite when
practical. Include migration/restart coverage for persistence changes and fixture
tests for adapters. Report changed files, exact commands/results, data migrations,
external verification status, and remaining blockers.
