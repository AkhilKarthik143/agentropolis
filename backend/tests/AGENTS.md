# Test-agent instructions

Tests must assert behavior and invariants, not implementation trivia. Use isolated
stores/simulations and deterministic seeds. Add a regression test for every bug
involving permissions, session scope, duplicate delivery/payment, inventory
reservation, legal transition, journal balance, reconciliation, or provider
uncertainty.

External tests must be explicit, opt-in, capped, and skipped/fail-closed without
credentials. Never print secrets or make a test depend on a production account.
Report exact command, count, warnings, and any provider/network limitation.
