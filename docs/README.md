# Agentropolis documentation

This directory explains the actual standalone implementation, its economic
invariants, sponsor boundaries, and the evidence required before a claim is made.
The root [README](../README.md) is the quick start; this index is the deeper
navigation point for developers and coding agents.

## Start here

- [Architecture](architecture.md) — process boundaries, persistence, events, and
  frontend transport.
- [Agent architecture](agent-architecture.md) — all 18 role types, permissions,
  messages, memory, and limits.
- [Domain model](domain-model.md) and [workflows](workflows.md) — contracts,
  inventory, fulfillment, approvals, accounting, and recovery.
- [Testing](testing.md), [demo](demo.md), and [final readiness](final-readiness.md)
  — reproducible commands, demo timing, and release claims.
- [Repository report](repository-report.md) — GitHub state, documentation inventory,
  verification, blockers, and next engineering tasks.
- [Security](security.md) — secrets, authorization limitations, payment safety,
  and deployment requirements.
- [Sponsor matrix](sponsor-matrix.md) — evidence-based integration status.
- [Implementation roadmap](implementation-roadmap.md) — ordered work with owners,
  dependencies, and acceptance criteria.

## Sponsor track guides

Each track has a human guide and an agent operating guide under
[`docs/tracks`](tracks/README.md). They distinguish the current local adapter or
product alignment from credential-backed external verification.

## Documentation rules

Documentation must name real files and commands. Planned work is labelled as
planned; fixture tests are not called external verification. Run
`python3 scripts/check_docs.py` after documentation changes. The check validates
local Markdown links and required track files without contacting provider APIs.

## Current status

The local backend is verified with 77 passing tests, repeatable isolated smoke,
and a real local uAgents exchange. The frontend redesign is concurrent and its
final acceptance is pending. Public Agentverse, Nessie, live Claude, x402
settlement, CRS, Solana, Creao, SpacetimeDB, and Figma evidence remain separate
gates; see [final-readiness](final-readiness.md).
