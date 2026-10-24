# Solana — independent development-network payment rail

## Goal and fit

Solana is a possible separate rail for an eligible digital-service purchase. It
must remain distinct from Coinbase x402: one invoice selects one rail and cannot be
settled twice. The current repository has no Solana adapter or verified transaction.

## Planned architecture

Add a typed server-side adapter under `backend/app/integrations/` only after the
official SDK/network contract is confirmed. Payments and Treasury authorize the
transaction; Accounting records the provider id and reconciliation state; a
Digital-Service Supplier delivers the result. The authoritative internal ledger
remains separate from chain confirmation.

## Current and missing functionality

Status is `NOT_STARTED`. Missing are official challenge requirements, devnet
network/asset, wallet custody plan, recipient allowlist, transaction confirmation,
uncertainty journal, fixtures, and a real workflow.

## Test, demo, definition of done

No Solana verifier exists. The future test suite must cover authorization, wrong
recipient, insufficient funds, duplicate submission, failed/uncertain confirmation,
and reconciliation. Done means an approved devnet transaction buys a useful
service, delivers its result, and produces one reconciled internal payment record;
mainnet and frontend keys are prohibited.
