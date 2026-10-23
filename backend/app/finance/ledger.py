from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Iterable


class Account(StrEnum):
    CASH = "Cash"
    ACCOUNTS_RECEIVABLE = "Accounts Receivable"
    INVENTORY = "Inventory"
    ACCOUNTS_PAYABLE = "Accounts Payable"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    COGS = "COGS"
    WRITE_OFF = "Write-offs/Fraud loss"
    FEES = "Fees"


@dataclass(frozen=True)
class LedgerLine:
    account: Account
    amount_cents: int
    business_id: str
    memo: str = ""


@dataclass(frozen=True)
class JournalEntry:
    entry_id: str
    business_id: str
    lines: tuple[LedgerLine, ...]
    memo: str = ""
    idempotency_key: str | None = None


class LedgerError(ValueError):
    pass


class Ledger:
    """Balanced double-entry journal. Amounts are integer cents only."""

    def __init__(self) -> None:
        self.entries: list[JournalEntry] = []
        self._by_idempotency: dict[str, JournalEntry] = {}
        self._lock = Lock()

    def post(self, entry: JournalEntry) -> JournalEntry:
        if not entry.lines:
            raise LedgerError("journal entry must contain at least two lines")
        if sum(line.amount_cents for line in entry.lines) != 0:
            raise LedgerError("journal entry is not balanced")
        if any(not isinstance(line.amount_cents, int) for line in entry.lines):
            raise LedgerError("ledger amounts must be integer cents")
        with self._lock:
            if entry.idempotency_key and entry.idempotency_key in self._by_idempotency:
                return self._by_idempotency[entry.idempotency_key]
            self.entries.append(entry)
            if entry.idempotency_key:
                self._by_idempotency[entry.idempotency_key] = entry
            return entry

    def seed_cash(self, business_id: str, cents: int) -> JournalEntry:
        if cents < 0:
            raise LedgerError("opening cash cannot be negative")
        return self.post(JournalEntry(
            entry_id=f"opening-{business_id}", business_id=business_id,
            lines=(LedgerLine(Account.CASH, cents, business_id, "Opening cash"), LedgerLine(Account.EQUITY, -cents, business_id, "Opening equity")),
            memo="Opening balance", idempotency_key=f"opening:{business_id}",
        ))

    def balances(self, business_id: str) -> dict[Account, int]:
        result = {account: 0 for account in Account}
        for entry in self.entries:
            for line in entry.lines:
                if line.business_id == business_id:
                    result[line.account] += line.amount_cents
        return result

    def balance(self, business_id: str, account: Account = Account.CASH) -> int:
        return self.balances(business_id).get(account, 0)

    def trial_balance(self, business_id: str | None = None) -> dict[str, int]:
        totals: dict[str, int] = {account.value: 0 for account in Account}
        for entry in self.entries:
            for line in entry.lines:
                if business_id is None or line.business_id == business_id:
                    totals[line.account.value] += line.amount_cents
        return totals

    def is_balanced(self, business_id: str | None = None) -> bool:
        return sum(self.trial_balance(business_id).values()) == 0

    def proof(self, business_id: str | None = None) -> dict:
        """Return an auditable debit/credit proof for the current journal."""

        per_account: dict[str, dict[str, int]] = {}
        total_debits = 0
        total_credits = 0
        entries = self.snapshot(business_id)
        for entry in entries:
            for line in entry["lines"]:
                account = line["account"]
                bucket = per_account.setdefault(account, {"debits_cents": 0, "credits_cents": 0, "net_cents": 0})
                amount = int(line["amount_cents"])
                if amount >= 0:
                    bucket["debits_cents"] += amount
                    total_debits += amount
                else:
                    bucket["credits_cents"] += -amount
                    total_credits += -amount
                bucket["net_cents"] += amount
        return {
            "business_id": business_id,
            "per_account": per_account,
            "total_debits_cents": total_debits,
            "total_credits_cents": total_credits,
            "balanced": total_debits == total_credits and self.is_balanced(business_id),
        }

    def snapshot(self, business_id: str | None = None) -> list[dict]:
        return [
            {"entry_id": entry.entry_id, "business_id": entry.business_id, "memo": entry.memo,
             "idempotency_key": entry.idempotency_key,
             "lines": [{"account": line.account.value, "amount_cents": line.amount_cents, "business_id": line.business_id, "memo": line.memo} for line in entry.lines]}
            for entry in self.entries if business_id is None or entry.business_id == business_id
        ]

