# Backend tests

Tests cover the local economic vertical slice, durable agent runtime, finance
invariants, API/session guards, event replay, provider contracts, and scenario
recovery. Tests are offline by default and use fixtures or deterministic local
transport.

Run the complete suite with `(cd backend && PYTHONPATH=. python3 -m pytest -q)`.
Targeted examples are `tests/test_economic_integrity.py`,
`tests/test_durable_agent_runtime.py`, `tests/test_external_adapters.py`,
`tests/test_scenarios.py`, and `tests/test_api_guards.py`. Do not treat a fixture
or replay pass as external sponsor verification.
