# Capital One Nessie — simulated banking

## Goal and product fit

Nessie can provide sandbox account/balance/transaction information for a business
whose internal ledger remains authoritative. Treasury reads the mapped account;
authorized payment submits a supported sandbox action; reconciliation compares the
provider result to the internal obligation. This is not real-world banking.

## Architecture and agents

`backend/app/integrations/nessie.py` is the HTTP adapter and
`backend/app/finance/banking.py`/`reconciliation.py` own the finance boundary.
Treasury, Payments, Accounting, and Controller participate. The adapter handles
query-key configuration, amount serialization, timeout classification, and
submission journaling.

## Current and missing functionality

Request/response fixtures, exact amounts, account mapping validation, duplicate
protection, timeout/uncertainty, and restart behavior are locally tested. No
credential-backed sandbox account or transfer was verified. Required variables are
`NESSIE_MODE=sandbox`, `NESSIE_API_KEY`, `NESSIE_BASE_URL`, and an approved
`NESSIE_ACCOUNT_ID` where the selected check needs one.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_external_adapters.py
tests/test_reconciliation.py)` and `python3 backend/scripts/verify_nessie.py`.
Without credentials the verifier must fail closed as `NOT VERIFIED`. The external
demo must show account mapping, balance, authorized sandbox action, provider status,
internal journal, and reconciliation.

## Definition of done

A sanitized Nessie sandbox trace succeeds without changing internal accounting
invariants. Never describe fixture or mock activity as a Nessie transfer.
