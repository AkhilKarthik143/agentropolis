# Solana implementation-agent instructions

Mission: implement a bounded devnet Solana payment rail only after official access
and event requirements are confirmed.

Until then, do not create a fake adapter or claim integration. When authorized,
own the typed provider client, payment-rail tests, verification script, and this
guide; coordinate finance/economy changes for the service-expense seam.

Require server-side signer custody, devnet allowlist, exact recipient/amount/asset,
persisted idempotency before submission, confirmation polling, explicit uncertain
state, and no cross-rail duplicate. Run fixture, authorization, failure, duplicate,
confirmation, and reconciliation tests plus an opt-in devnet check. Update env,
setup, matrix, security, and final readiness; never commit keys.
