# Visa — autonomous shopping

## Goal and product fit

Agentropolis makes procurement explainable: a buyer detects a need, discovers
multiple suppliers, receives independent quotes, negotiates, scores price/delivery/
availability/risk, and requests approval before purchasing. The current workflow
is a local product capability aligned with autonomous shopping; no Visa API claim is
made.

## Architecture and agents

Procurement, Broker, Negotiation, Supplier, Treasury, and Risk roles use
`backend/app/agents/`, `backend/app/economy/scoring.py`, supplier catalogs, and the
negotiation/contract engine. The frontend procurement route visualizes competing
offers, rationale, approval, and downstream fulfillment.

## Current and missing functionality

Local supplier comparison, business policies, risk checks, budget validation,
counteroffers, expiration, human approval, reservation, receipt, and accounting
are implemented/tested. A Visa-specific API or tokenized checkout is not connected.
The exact sponsor challenge and eligible APIs must be supplied before choosing an
integration.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_engine.py
tests/test_scenarios.py tests/test_economic_integrity.py)`, then follow the three-
minute flow in [demo.md](../../demo.md): show at least three offers, a counteroffer,
why the winner was selected, approval, receipt, and separate payment/reconciliation.

## Definition of done

The shopping workflow is understandable, policy-controlled, and backed by real
events. A Visa-specific submission additionally requires documented API/eligibility
evidence and must not be inferred from product alignment.
