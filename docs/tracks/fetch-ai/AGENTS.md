# Fetch.ai implementation-agent instructions

Mission: preserve safe local uAgents transport and add public Agentverse operation
only with an approved reachable deployment.

Own `backend/app/integrations/fetch_ai.py`, `backend/app/agents/transport.py`,
verification scripts, transport tests, and this guide. Keep `AgentRegistry` and
the local durable queue authoritative for message permissions and economic effects.

Require typed schema/version, sender/recipient identity, business/session scope,
correlation and idempotency, acknowledgement, timeout, retry and expiry. Public
endpoint and registration are separate gates; local dispatch never upgrades the
status. Never expose seeds or Agentverse keys.

Run local uAgents verification, transport/role tests, and opt-in public checks.
Acceptance requires sanitized external discovery/exchange evidence. Update setup,
matrix, final readiness, and architecture docs; report endpoint/registration
blockers without claiming reachability.
