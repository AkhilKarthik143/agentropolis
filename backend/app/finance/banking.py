from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class BankTransaction:
    transaction_id: str
    from_account: str
    to_account: str
    amount_cents: int
    memo: str
    idempotency_key: str


class BankError(RuntimeError):
    pass


class BankAdapter(Protocol):
    mode: str

    def create_account(self, business_id: str, opening_cents: int = 0) -> str: ...
    def transfer(self, from_account: str, to_account: str, amount_cents: int, memo: str, idempotency_key: str) -> BankTransaction: ...
    def history(self, account_id: str | None = None) -> list[BankTransaction]: ...
    def balance(self, account_id: str) -> int: ...


class MockBank:
    mode = "mock"

    def __init__(self) -> None:
        self.accounts: dict[str, int] = {}
        self.transactions: list[BankTransaction] = []
        self._idempotency: dict[str, BankTransaction] = {}
        self._lock = Lock()
        self._counter = 0

    def create_account(self, business_id: str, opening_cents: int = 0) -> str:
        account_id = f"mock_acct_{business_id}"
        with self._lock:
            self.accounts.setdefault(account_id, opening_cents)
        return account_id

    def transfer(self, from_account: str, to_account: str, amount_cents: int, memo: str, idempotency_key: str) -> BankTransaction:
        if amount_cents <= 0:
            raise BankError("transfer amount must be positive")
        with self._lock:
            if idempotency_key in self._idempotency:
                return self._idempotency[idempotency_key]
            if self.accounts.get(from_account, 0) < amount_cents:
                raise BankError("insufficient bank funds")
            if to_account not in self.accounts:
                raise BankError("destination bank account not found")
            self.accounts[from_account] -= amount_cents
            self.accounts[to_account] += amount_cents
            self._counter += 1
            transaction = BankTransaction(f"banktx_{self._counter:04d}", from_account, to_account, amount_cents, memo, idempotency_key)
            self.transactions.append(transaction)
            self._idempotency[idempotency_key] = transaction
            return transaction

    def history(self, account_id: str | None = None) -> list[BankTransaction]:
        if account_id is None:
            return list(self.transactions)
        return [tx for tx in self.transactions if tx.from_account == account_id or tx.to_account == account_id]

    def balance(self, account_id: str) -> int:
        return self.accounts.get(account_id, 0)

