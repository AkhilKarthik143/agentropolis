# Migration-agent instructions

Add forward-only numbered SQL for schema changes. Document columns, indexes,
constraints, transaction assumptions, and any backfill. Do not delete or rewrite
existing migration history and do not edit generated databases in the repository.

Run the backend suite plus fresh-store, restart/reload, duplicate/idempotency, and
reset/checkpoint tests. Confirm event/snapshot and runtime-store consistency. Report
upgrade compatibility and whether a demo reset is required.
