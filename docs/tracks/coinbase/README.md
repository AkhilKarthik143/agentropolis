# Coinbase Payment Agents — x402 digital services

## Goal and product fit

An Agentropolis business should discover a useful digital service, authorize its
price, pay through a supported x402 HTTP resource, receive the result, post a
service expense, and reconcile the payment. This is a separate digital-service
workflow, not a second way to settle a physical inventory invoice.

## Architecture and agents

The guarded adapter is `backend/app/integrations/coinbase_x402.py`; budget and
payment controls live in `backend/app/finance/` and `economy/engine.py`. Procurement,
Digital-Service Supplier, Treasury, Payments, and Accounting participate. The
adapter validates challenge version, HTTPS origin, Base Sepolia/network, token,
recipient, amount caps, signer, provider settlement, and receipt before success.

## Current and missing functionality

Challenge/signing behavior and safety rejection paths are fixture-tested. No
credential-backed payment or external transfer was executed, and the adapter is
not yet connected to a complete service-expense/report-delivery accounting path.
Required access is an approved test resource, throwaway capped wallet, test USDC,
recipient, and explicit authorization. Mainnet is prohibited by default.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_external_adapters.py
tests/test_sponsor_controls.py)` and `python3 backend/scripts/verify_x402.py`.
Without testnet configuration the verifier must say `NOT VERIFIED`. The completed
demo must show discovery, authorization, one payment, useful report delivery,
expense posting, provider receipt, and reconciliation with no duplicate retry.

## Definition of done

One supported x402 digital-service purchase succeeds on the approved test network,
is auditable end to end, and cannot pay twice. Fixture-only adapter success is not
external verification.
