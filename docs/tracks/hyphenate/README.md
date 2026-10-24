# Hyphenate — autonomous finance department

## Goal and product fit

Agentropolis demonstrates a finance team operating an AI business: treasury checks
reserves, AP matches invoices, risk/controller enforce controls, payments submit an
approved obligation, accounting posts balanced entries, and reconciliation checks
the result. The workflow is implemented locally; Hyphenate API or eligibility is
not claimed.

## Architecture and agents

The workflow spans `backend/app/finance/`, `backend/app/agents/financial_operations.py`,
`backend/app/economy/engine.py`, and `backend/app/events/`. Required roles are
Treasury, Payments, Accounting, Accounts Payable, Accounts Receivable, Controller,
and Risk. Receipt creates inventory/AP and seller AR/revenue/COGS; payment is a
separate authorized transition.

## Current and missing functionality

Local balances use integer cents, entity-scoped double-entry journals, approval
thresholds, invoice holds, duplicate protection, failed/uncertain payment states,
and reconciliation. Missing are a verified Hyphenate-specific API/workflow and
production authentication/tenant authorization. Check [sponsor matrix](../../sponsor-matrix.md)
for evidence.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_ledger.py
tests/test_reconciliation.py tests/test_economic_integrity.py)`, then use the
purchase/receipt/payment flow in [demo.md](../../demo.md). Demonstrate a duplicate
invoice or insufficient-funds hold. External submission requires the official
challenge brief, sanitized trace, and a real Hyphenate-specific requirement if one
exists.

## Definition of done

The finance workflow completes end to end with balanced buyer/seller books, blocked
unsafe cases, traceable approvals, and verified challenge alignment. Do not call the
track externally verified merely because the local finance department works.
