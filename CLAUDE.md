# Claude Code instructions for Agentropolis

Read the repository-root `AGENTS.md` and the nearest subsystem `AGENTS.md` before
working. Agentropolis is standalone; AgentPlace is not a dependency or a source of
code. Preserve the trusted-command boundary: Claude may propose structured
decisions, but it must not directly mutate balances, inventory, contracts, or
journals.

Use deterministic/replay mode by default. Live Claude calls require explicit
configuration, bounded budgets, timeouts, schema validation, provenance, and a
clear test result. Never expose `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY` in output.

Inspect Git status before editing, preserve concurrent changes, and do not modify
the active frontend redesign without coordination. Run focused tests plus the
repository preflight when practical. Final reports must separate local simulation,
fixture evidence, and credential-backed external verification.
