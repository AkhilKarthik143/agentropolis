"""Accounting service facade; the Ledger remains the source of truth."""

from __future__ import annotations

from .banking import BankAdapter
from .ledger import JournalEntry, Ledger
from .reconciliation import ReconciliationResult, reconcile_business


class AccountingService:
    role = "accounting_service"

    def __init__(self, ledger: Ledger, bank: BankAdapter) -> None:
        self.ledger = ledger
        self.bank = bank

    def post(self, entry: JournalEntry) -> JournalEntry:
        return self.ledger.post(entry)

    def reconcile(self, business_id: str, account_id: str) -> ReconciliationResult:
        return reconcile_business(business_id, account_id, self.ledger, self.bank)  # type: ignore[arg-type]

    def proof(self, business_id: str | None = None) -> dict:
        return self.ledger.proof(business_id)
