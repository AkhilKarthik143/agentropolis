# Database coding-agent instructions

- Add a numbered migration for schema changes; never silently mutate existing
  tables at import time.
- Document transaction boundaries and rollback behavior.
- Preserve event/snapshot consistency, idempotency keys, simulation isolation, and
  durable retry leases.
- Keep private agent memory separate from public event projections.
- Exercise a fresh store, restart/reload, duplicate command, and reset path for
  persistence changes.
- Never commit `backend/.data`, WAL files, or provider credentials.

Required report: migration names, compatibility/backfill behavior, tests run, and
whether old local data needs a reset.
