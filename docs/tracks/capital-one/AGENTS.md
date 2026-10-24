# Capital One Nessie implementation-agent instructions

Mission: maintain a safe Nessie sandbox adapter and its reconciliation boundary.

Own `backend/app/integrations/nessie.py`, banking/reconciliation adapter seams,
fixtures, `verify_nessie.py`, and this guide. Do not let Treasury construct HTTP
requests or let provider data directly mutate the ledger.

Validate query-key configuration, account ownership/mapping, exact cents, timeout,
provider transaction identity, duplicate submission, and uncertain outcome. Keep
the default mode mock/local and require explicit `NESSIE_MODE=sandbox`.

Run adapter/reconciliation/integrity tests and the verifier. Acceptance requires a
real approved sandbox response, sanitized evidence, and a reconciled internal
record. Update `.env.example`, setup, sponsor matrix, and final readiness. Never
log the API key or copy a user’s bank credentials.
