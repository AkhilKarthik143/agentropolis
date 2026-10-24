# Agentropolis implementation roadmap

This roadmap is an executable backlog for the standalone repository. It preserves
the working local economy while making sponsor work incremental and reversible.

| Phase | Owner | Dependencies | Acceptance evidence | Status |
| --- | --- | --- | --- | --- |
| 1. Documentation and boundaries | Maintainers | Current source and test audit | Root/subsystem guides, sponsor guides, link check, no AgentPlace runtime dependency | IN_PROGRESS |
| 2. Core economy stabilization | Economy + finance | Existing engine, stores, seed | Full backend suite, smoke twice, restart/isolation/integrity tests | LOCAL_VERIFIED |
| 3. Sponsor foundation | Integration maintainers | Typed adapters, `.env.example`, fixture tests | Each adapter has config validation, timeout/error policy, fixture coverage, and status entry | MOCK_TESTED |
| 4. Primary sponsor completion | Fetch, Nessie, x402, Claude, procurement | Human credentials and approved sandbox/testnet resources | Sanitized external evidence for each selected track; no unapproved transfer | BLOCKED_ON_ACCESS |
| 5. Additional sponsor completion | CRS, Solana, Creao, SpacetimeDB | Official event contracts and credentials/platform access | Genuine workflow, provider-specific tests, demo trace, and updated status | PLANNED |
| 6. Frontend integration | Frontend owner | Stable API/event contracts and handoff | Build, lint, eight browser cases, responsive screenshots, reduced-motion check | PENDING_HANDOFF |
| 7. Verification and hardening | Release lead | Completed feature branches | Fresh install, Docker, multi-browser, security, accessibility, outage/retry tests | PLANNED |
| 8. Submission package | Release lead + user | Exact event brief and final evidence | Three-minute demo, source map, architecture diagram, screenshots/video, accurate sponsor claims | PLANNED |

## Phase 1 — documentation and architecture

- Keep root and subsystem instructions close to the code they govern.
- Link every sponsor guide to real adapter, agent, test, and environment paths.
- Run `python3 scripts/check_docs.py`; resolve broken local links and contradictory
  status claims before merging.
- Record missing credentials in `docs/USER_SETUP_REQUIRED.md`, never in source.

## Phase 2 — core economy stabilization

- Preserve the trusted `EconomyEngine` boundary and SQLite event/snapshot writes.
- Keep supplier quotes independent, inventory reservations before acceptance, and
  payment distinct from receipt and reconciliation.
- Add larger-world, long-running, and provider-outage tests only after the current
  suite remains green.

## Phase 3 — sponsor foundation

Every adapter must expose explicit configuration, typed request/response handling,
timeouts, safe retry rules, idempotency, audit metadata, and fixture tests. The
adapter must not silently switch local economic settlement to a provider merely
because an API key is present.

## Phase 4 and 5 — sponsor workflows

Implement one end-to-end vertical slice at a time: discovery or need, agent
proposal, trusted authorization, provider action, result delivery, accounting,
reconciliation, and an auditable UI/event trace. Use sandbox/testnet resources and
require an explicit human-provided recipient or account mapping.

## Phase 6 through 8 — release

Frontend ownership must be explicitly handed back before editing overlapping UI
files. Then run the final UI matrix, fresh-machine and Docker checks, secret scan,
and the timed demo. A sponsor remains `MOCK_TESTED` or `LOCAL_VERIFIED` until the
provider exchange and its business result are captured and documented.
