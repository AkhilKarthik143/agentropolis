# Events coding-agent instructions

Keep event schemas typed, versionable, serializable, scoped to a simulation and
business where applicable, and safe to replay. Preserve sequence ordering,
idempotency keys, hash-chain verification, WebSocket catch-up, and reset signaling.

Do not put secrets or private agent memory in public event payloads. Do not make a
projection store authoritative for financial writes without a documented migration
and consistency model. Run `tests/test_bus.py`, `tests/test_replay.py`, and API
WebSocket/reset tests for stream changes.
