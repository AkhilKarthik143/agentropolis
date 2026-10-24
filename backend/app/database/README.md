# Database and migrations

`app/database` owns migration discovery and application. Economic events and
snapshots are stored by the event/economy persistence components; durable agent
tasks, messages, agents, memory and negotiations use the runtime store. The current
local authority is SQLite under `backend/.data/`, with a fresh database per
simulation session and recoverable reset checkpoints.

Migrations are ordered SQL files in `backend/migrations/`. Current files create the
event chain, economic snapshots, and agent-runtime tables. State changes that cross
economic and event boundaries must be transactional and restart-safe.

Run backend tests with `(cd backend && PYTHONPATH=. python3 -m pytest -q)`. Do not
delete or hand-edit a user's database as part of a normal code change; use the reset
endpoint only for the local demo and preserve the checkpoint behavior.
