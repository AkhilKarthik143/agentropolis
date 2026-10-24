# Database migrations

Migration SQL is applied by the standalone backend migration helper. Files are
numbered in order: the event/audit schema, economic snapshots, and durable agent
runtime tables. Migrations are part of the data contract and must remain compatible
with the reset/checkpoint and restart flows.

There is no production migration claim yet. Verify a fresh store and an existing
local store before shipping schema changes; keep generated `.db`, WAL, and SHM
files ignored.
