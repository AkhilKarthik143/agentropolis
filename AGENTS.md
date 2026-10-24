# Agentropolis coding-agent instructions

## Mission and boundary

Agentropolis is an independent monorepo for a local autonomous-business economy.
The reference project, AgentPlace, is inspiration only. Do not import its code,
assets, prompts, database, Git history, environment variables, or server. Do not
start, modify, or inspect AgentPlace as part of an Agentropolis change.

## Before editing

1. Read the nearest `AGENTS.md` and the relevant README.
2. Run `git status --short --untracked-files=all` and inspect the changed paths.
3. Preserve uncommitted work belonging to another agent. Do not reset, checkout,
   clean, force-push, or overwrite a file with active ownership.
4. Inspect the actual implementation and tests before documenting or changing it.

## Architecture rules

- Agents propose typed actions; trusted economy and finance services validate and
  execute them.
- Keep domain/economic rules independent from provider HTTP clients and React.
- Preserve business and simulation isolation, message idempotency, inventory
  reservations, approval gates, integer-cent money, balanced entity journals,
  and explicit reconciliation.
- External sponsor adapters are optional, configured through environment variables,
  and must never be required for the local demo.
- A local fixture, replay, or mock is not external verification. Update
  `docs/sponsor-matrix.md` only with evidence that actually exists.
- Never put secrets, private keys, real account identifiers, or generated SQLite
  databases in Git. Use sandbox/testnet credentials only and cap any permitted
  provider action.

## Scope and collaboration

Use a branch or worktree for substantial isolated work. Keep changes narrow and
prefer additive documentation when another agent owns the overlapping source.
Frontend source is currently subject to concurrent ownership; coordinate before
editing `frontend/src`, `frontend/tests`, or frontend configuration.

## Verification

At minimum, run the relevant focused tests and report the exact commands. For a
backend change, use `(cd backend && PYTHONPATH=. python3 -m pytest -q)` when the
full suite is appropriate. For a local release check, run `./scripts/preflight.sh`.
Run `python3 scripts/check_docs.py` after documentation changes. Do not claim a
green frontend build or external sponsor workflow unless that command/evidence was
run against the current source.

## Completion report

Every agent must report: files changed, behavior implemented, tests run and their
results, external integrations verified or not verified, remaining blockers, user
credentials/actions required, and any concurrent work left untouched.
