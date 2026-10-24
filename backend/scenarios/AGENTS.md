# Scenario coding-agent instructions

Keep seed data deterministic, internally consistent, and clearly labelled as
simulation input. Add a scenario only with a named trigger, expected causal
sequence, recovery/no-recovery outcome, and backend test. Do not encode a winning
supplier or payment result in a way that bypasses the normal agents and engine.

Run `tests/test_scenarios.py`, relevant engine/integrity tests, and
`bash backend/scripts/demo_smoke.sh --full`. Update `docs/demo.md` and
`docs/final-readiness.md` if the presenter flow or safe claims change.
