from __future__ import annotations

from dataclasses import dataclass

from .banking import BankTransaction, MockBank
from .ledger import Account, Ledger


@dataclass(frozen=True)
class ReconciliationResult:
    ok: bool
    business_id: str
    ledger_cash_cents: int
    bank_cash_cents: int
    mismatch_cents: int
    reason: str = ""


def reconcile_business(business_id: str, account_id: str, ledger: Ledger, bank: MockBank) -> ReconciliationResult:
    ledger_cash = ledger.balance(business_id, Account.CASH)
    bank_cash = bank.balance(account_id)
    mismatch = bank_cash - ledger_cash
    return ReconciliationResult(ok=mismatch == 0, business_id=business_id, ledger_cash_cents=ledger_cash, bank_cash_cents=bank_cash, mismatch_cents=mismatch, reason="" if mismatch == 0 else "bank balance differs from ledger cash")

