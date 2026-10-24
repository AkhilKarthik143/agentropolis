# CRS Credit — counterparty risk

## Goal and product fit

Risk and Credit should use supported CRS sandbox information to produce an
explainable recommendation for a high-value supplier or simulated financing
request. The recommendation influences policy; it does not issue real credit or
invent sensitive attributes.

## Architecture and agents

The current seam is `backend/app/integrations/crs_credit.py`; Risk and Credit
roles are in `backend/app/agents/risk.py` and `financial_operations.py`. The
economy engine consumes only a bounded policy result. No live CRS endpoint is
configured in the current repository.

## Current and missing functionality

Deterministic mock credit responses and local risk/affordability behavior are
available for tests. Missing are the official CRS API contract, approved test
identities, credentials, sensitive-data policy, and a credential-backed demo.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_external_adapters.py
tests/test_role_guards.py tests/test_economic_integrity.py)`. The target demo is a
counterparty assessment before a high-value contract, showing input provenance,
explanation, controller decision, and no automatic lending.

## Definition of done

Approved CRS sandbox data materially influences a legitimate simulated decision,
with validated fields, least-privilege handling, sanitized evidence, and no
fabricated credit outcome.
