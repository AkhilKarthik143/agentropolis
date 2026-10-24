# Agent implementation instructions

### Responsibility

Own role behavior, identity, permissions, message schemas, private memory and
agent-specific tests. Do not move economic authority into a handler.

### Safe implementation pattern

1. Read `BaseBusinessAgent`, `AgentContext`, `AgentRegistry`, and the message/event
   schema before changing a role.
2. Define the role's objective and minimal permissions explicitly.
3. Validate business/session/role scope through the context and registry.
4. Emit typed proposals or reviews with correlation and idempotency keys.
5. Let `EconomyEngine` or finance commands decide and execute the effect.
6. Persist only role-owned memory; never leak private notes into public projections.

Cross-business traffic is limited to RFQ, quote, and counteroffer messages. A retry
must be safe and a duplicate must not create another contract or payment.

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_agent_runtime.py
tests/test_durable_agent_runtime.py tests/test_role_guards.py tests/test_transport_fetch.py)`
and the full suite for shared runtime changes. Report role authority, message kinds,
and any migration or seed changes.
