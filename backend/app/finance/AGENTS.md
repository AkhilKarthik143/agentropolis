# Finance coding-agent instructions

The finance agent owns reviews and proposals; the trusted finance/economy command
owns journal and payment effects. Preserve double-entry balance, entity scope,
approval thresholds, invoice matching, payment idempotency, and explicit
reconciliation across every rail.

When adding a provider, define a typed rail result with provider id, amount,
recipient/account, status, and uncertainty. Persist a submission journal before
any external side effect and require a stable idempotency key. Never log secrets or
use a live account in tests.

Run ledger, approval, reconciliation, economic-integrity, and relevant adapter
tests. Add failure/timeout/duplicate/uncertain cases. Report whether the evidence
is mock, local, sandbox, testnet, or external.
