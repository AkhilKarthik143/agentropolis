# Orchestration coding-agent instructions

Preserve durable task/message state, simulation clocks, lease expiry, retry
backoff/dead-letter behavior, role permissions, active-agent identity, and
restart recovery. A scheduler may trigger a trusted command; it may not perform an
economic mutation by bypassing the engine.

When changing delivery, test duplicate messages, expired leases, unavailable
recipients, dead letters, session isolation, and restart/reload. When changing
tick order, document the causal sequence and update the scenario smoke. Do not
assume local in-process delivery proves public Fetch.ai communication.
