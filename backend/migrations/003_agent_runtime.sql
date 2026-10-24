-- Session-scoped agent work is durable independently of the event timeline.
CREATE TABLE IF NOT EXISTS agent_runtime_agents (
 simulation_id TEXT NOT NULL, agent_id TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (simulation_id, agent_id)
);
CREATE TABLE IF NOT EXISTS agent_runtime_messages (
 simulation_id TEXT NOT NULL, message_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
 available_tick INTEGER NOT NULL, expires_tick INTEGER NOT NULL,
 lease_until REAL, lease_owner TEXT, last_error TEXT, acknowledged_at TEXT,
 PRIMARY KEY (simulation_id, message_id), UNIQUE (simulation_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS agent_messages_ready ON agent_runtime_messages(simulation_id, status, available_tick);
CREATE TABLE IF NOT EXISTS agent_runtime_tasks (
 simulation_id TEXT NOT NULL, task_id TEXT NOT NULL, correlation_id TEXT,
 assigned_agent_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (simulation_id, task_id)
);
CREATE TABLE IF NOT EXISTS agent_runtime_negotiations (
 simulation_id TEXT NOT NULL, negotiation_id TEXT NOT NULL, business_id TEXT NOT NULL,
 status TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (simulation_id, negotiation_id)
);
CREATE TABLE IF NOT EXISTS agent_runtime_memory (
 simulation_id TEXT NOT NULL, agent_id TEXT NOT NULL, memory_key TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (simulation_id, agent_id, memory_key)
);
