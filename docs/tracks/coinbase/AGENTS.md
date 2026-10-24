# Coinbase/x402 implementation-agent instructions

Mission: complete a bounded digital-service purchase without mixing x402 with
physical-goods settlement.

Own `backend/app/integrations/coinbase_x402.py`, its tests and verification script,
plus the minimal finance/economy service-expense seam needed for the workflow.
Coordinate API/frontend changes before editing them.

Require HTTPS resource origin, approved recipient, Base Sepolia, exact currency and
amount, per-call/daily caps, server-side signer, persisted submission idempotency,
provider settlement and chain receipt. An uncertain response must remain uncertain;
never auto-retry a signed request. Keep wallet keys out of browser/source/logs.

Run adapter fixtures, sponsor controls, full backend tests, and the explicit
testnet verifier only with user-approved throwaway resources. Acceptance requires a
sanitized receipt plus delivered report and balanced service-expense records.
Update the track, matrix, setup, and final-readiness docs; report network, wallet,
recipient, and accounting blockers without exposing secrets.
