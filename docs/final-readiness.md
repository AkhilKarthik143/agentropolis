# Agentropolis final readiness

Evidence date: October 23, 2026. This is the release boundary for the standalone
`agentropolis` repository. AgentPlace is not part of this checkout, is not started
by its scripts, and was not modified by this pass.

## Verdict

The local backend and repeatable economy demo are ready for a controlled hackathon
demo. The complete sponsor-integrated and publicly deployable brief is not yet
accepted. External credentials, a final frontend handoff, and the paid digital
service workflow are still required before making those claims.

## Evidence completed in this pass

| Check | Result | Scope |
| --- | --- | --- |
| `cd backend && PYTHONPATH=. python3 -m pytest -q` | 77 passed | Local backend, persistence, economic integrity, role guards and adapter fixtures |
| `bash backend/scripts/demo_smoke.sh --full` | Passed twice | Reset, supplier failure/recovery, receipt, single settlement, reconciliation and ordered WebSocket catch-up |
| `cd backend && PYTHONPATH=. python3 scripts/verify_fetch.py` | Passed | Actual local uAgents dispatch between distinct buyer and seller addresses; `agentverse_verified=false` |
| Secret scan | Clean | No tracked `.env`; no configured hack-ship secret-pattern match |
| `scripts/preflight.sh` | Added | Repeatable local release gate; intentionally reports external gates separately |
| `scripts/reset_demo.sh` | Added | Loopback-only reset command for rehearsals |

The local proof uses simulated banking, credit, demand and fulfillment. It does not
move real money or imply a public Agentverse deployment.

## Sponsor acceptance matrix

| Sponsor / track | Local status | Release status |
| --- | --- | --- |
| Fetch.ai / Agentverse | Real local uAgents message exchange; typed protocol and distinct identities | **Pending** public registration, reachable endpoint and external discovery/exchange |
| Capital One Nessie | Adapter, request/response parsing, idempotency and fixture tests | **Pending** sandbox key, account mapping and a sanitized read-only/transfer evidence run |
| Coinbase x402 | Guarded v2 challenge/signing adapter and fixture tests | **Pending** approved Base Sepolia service, throwaway wallet, test USDC, provider settlement and receipt; not yet wired to service-expense accounting |
| Anthropic / Claude | Structured gateway, role prompts, budgets and replay/fixture tests | **Pending** credential-backed live response with cost/provenance evidence |
| Visa / Hyphenate | Procurement and finance concepts represented in the local product | **Pending** official API/track contract and credential-backed workflow; no integration claim |
| Apify | Dataset normalization and source metadata adapter | **Pending** selected Actor, token and completed dataset evidence |
| Figma / Paper | Paper reference inspected; local design notes retained | **Pending** requested Figma artifact/submission evidence |
| SpacetimeDB / Microsoft / CRS | Not implemented or only represented as product alignment/fixtures | **Not claimed** |

The detailed adapter boundaries and source contracts are in
[sponsor-matrix.md](sponsor-matrix.md). Official source contracts reviewed for the
implementation include [Fetch Agentverse onboarding](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents),
[Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
[Coinbase x402 buyer documentation](https://docs.cdp.coinbase.com/x402/buyer/quickstart),
and [Visa Intelligent Commerce](https://developer.visa.com/capabilities/visa-intelligent-commerce/overview).

## Product and architecture acceptance

Verified in the local system:

- Ten seeded businesses with 113 role instances across the eighteen role types.
- Business-owned identities, scoped messages, durable tasks, private memory and
  restart-safe SQLite state.
- Independent supplier catalogs, quotes and counteroffers.
- Inventory reservation before acceptance; separate shipping, receipt, invoice,
  payment and reconciliation states.
- Integer-cent double-entry journals for buyer and seller entities, duplicate
  protection, uncertain-payment handling and recoverable reset checkpoints.
- Deterministic local economy controls with explicit human approval for threshold
  purchases and a visible local-simulation disclosure.

The default runtime is one local process with company-owned agents and a trusted
`EconomyEngine` command boundary. This is appropriate for a demo; it is not yet a
multi-tenant production authorization boundary.

## Frontend handoff gate

The frontend is being redesigned by a concurrent agent. Its source files were left
untouched during this release pass. The earlier six-case browser snapshot is not
evidence for that redesign; the latest overlapping run was 2 passed / 6 failed.
Before calling the project complete, the frontend owner must return a clean handoff
with:

1. `npm run build` passing.
2. `npm run lint` passing.
3. The eight browser cases passing at desktop and 390 px mobile widths.
4. World, negotiation, control-tower, procurement, business and scenario routes
   rendering against a freshly reset demo.
5. Fresh screenshots and a short interaction record for the final source.

## Three-minute demo gate

Use [demo.md](demo.md) for the timed script. The safe local sequence is:

```sh
./scripts/preflight.sh
./scripts/reset_demo.sh
./scripts/dev.sh
```

If a provider or live integration is unavailable, keep the local simulation running,
show the adapter status as pending, and do not substitute fixture output for an
external claim. If the UI state becomes unclear, stop the clock, run the reset
script, reload the dashboard, and use the recorded local smoke result as the
fallback. Never point `reset_demo.sh` at another project or a non-loopback server.

## Security and deployment boundary

- Keep `.env` private; `.env.example` contains placeholders only.
- Do not copy AgentPlace credentials, databases or environment files.
- Do not enable mainnet settlement. x402 testing must use a throwaway, capped
  Base Sepolia wallet and an explicitly approved recipient.
- The current API is a trusted local operator surface: authentication, tenant
  authorization, managed secret storage, provider reconciliation workers and
  production observability remain before public deployment.
- Docker configuration exists but was not executed in this pass; no fresh-machine,
  multi-browser, formal accessibility or public-deployment claim is made.

## Safe claims for judging

It is safe to say that Agentropolis is a standalone local multi-agent economy with
durable business-owned agents, deterministic financial controls, independent
negotiation, recovery from supplier shocks, and a repeatable local proof.

Do not say that Agentverse is publicly reachable, Nessie transferred funds, Claude
answered live, an x402 service purchase settled, Apify data was live, a Figma
artifact was delivered, or Agentropolis is production-ready until the corresponding
evidence is added to this document and the sponsor matrix.

## Required user access

See [USER_SETUP_REQUIRED.md](USER_SETUP_REQUIRED.md) for the exact credentials,
accounts, safety limits and commands needed to close the pending gates. No secrets
should be pasted into chat or committed to this repository.
