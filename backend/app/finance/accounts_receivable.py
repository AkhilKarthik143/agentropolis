"""Small deterministic accounts-receivable register for the demo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock


@dataclass(frozen=True)
class Receivable:
    receivable_id: str
    business_id: str
    customer_id: str
    amount_cents: int
    due_date: str
    status: str = "outstanding"


class AccountsReceivableService:
    role = "accounts_receivable"

    def __init__(self) -> None:
        self.receivables: list[Receivable] = []
        self._lock = Lock()

    def record(self, receivable: Receivable) -> Receivable:
        if receivable.amount_cents <= 0:
            raise ValueError("receivable amount must be positive")
        with self._lock:
            existing = next((item for item in self.receivables if item.receivable_id == receivable.receivable_id), None)
            if existing:
                return existing
            self.receivables.append(receivable)
        return receivable

    def settle(self, receivable_id: str) -> Receivable:
        with self._lock:
            for index, item in enumerate(self.receivables):
                if item.receivable_id == receivable_id:
                    settled = Receivable(**{**asdict(item), "status": "settled"})
                    self.receivables[index] = settled
                    return settled
        raise KeyError(receivable_id)

    def snapshot(self) -> list[dict]:
        return [asdict(item) for item in self.receivables]
