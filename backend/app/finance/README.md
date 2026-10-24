# Finance and controls

Finance models the autonomous finance department: treasury/reserves, approvals,
double-entry journals, invoices, AP/AR, payment rails, controller exceptions,
banking adapters, and reconciliation. It works with the economy engine but does
not own contracts or inventory.

Important files are `ledger.py`, `accounting.py`, `accounts_payable.py`,
`accounts_receivable.py`, `approvals.py`, `controls.py`, `treasury.py`,
`banking.py`, and `reconciliation.py`. Receipt posts buyer inventory/AP and seller
AR/revenue/COGS; a matched invoice and authorization are required before payment;
provider outcomes are reconciled separately.

## Financial invariants

- Use integer cents and balance each legal entity independently.
- Never pay a duplicate transaction identifier.
- Failed and uncertain provider results remain visible and require reconciliation;
  an uncertain result is not an automatic retry license.
- Approval terms are exact and bound to the contract/proposal.
- Simulated cash is not external bank settlement.

Run `tests/test_ledger.py`, `tests/test_reconciliation.py`,
`tests/test_economic_integrity.py`, and the full backend suite.
