# Agent orchestration runtime

`app/orchestration` runs business-owned agents over simulation ticks. `runtime.py`
creates the role registry, processes clock work, drains durable messages, advances
fulfillment/recovery, and keeps the agent world connected to the economy engine.
`store.py` persists agents, tasks, messages, negotiations, and private memory.

Delivery is at least once with leases, retries, expiry, and dead letters. An
acknowledged message means a handler returned; it does not mean a contract or
payment succeeded. Economic commands remain idempotent and authoritative.

Start the application with `./scripts/dev.sh`. Runtime coverage is in
`tests/test_agent_runtime.py`, `test_durable_agent_runtime.py`, `test_bus.py`, and
the scenario/API tests.
