from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentReceipt:
    receipt_id: str
    amount_cents: int
    network: str
    tx_hash: str
    mode: str


class PaymentRail(Protocol):
    mode: str

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt: ...


class X402Adapter(PaymentRail, Protocol):
    """Adapter boundary for a paid agent-to-agent HTTP call."""


class MockX402:
    mode = "mock"

    def __init__(self, *, per_call_cap_cents: int = 2_500, daily_cap_cents: int = 10_000) -> None:
        self.per_call_cap_cents = per_call_cap_cents
        self.daily_cap_cents = daily_cap_cents
        self.spent_cents = 0
        self._receipts: dict[str, PaymentReceipt] = {}

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if idempotency_key in self._receipts:
            return self._receipts[idempotency_key]
        if amount_cents <= 0 or amount_cents > self.per_call_cap_cents:
            raise ValueError("x402 per-call spend cap exceeded")
        if self.spent_cents + amount_cents > self.daily_cap_cents:
            raise ValueError("x402 daily spend cap exceeded")
        receipt = PaymentReceipt(f"receipt_{idempotency_key[:10]}", amount_cents, "mock-testnet", f"mocktx_{idempotency_key[:12]}", self.mode)
        self.spent_cents += amount_cents
        self._receipts[idempotency_key] = receipt
        return receipt


class X402Testnet:
    mode = "testnet"

    def __init__(self, network: str, *, per_call_cap_cents: int = 2_500, daily_cap_cents: int = 10_000) -> None:
        allowed = {"base-sepolia", "ethereum-sepolia", "solana-devnet"}
        if network not in allowed:
            raise ValueError("x402 adapter refuses unknown or mainnet networks")
        self.network = network
        self.per_call_cap_cents = per_call_cap_cents
        self.daily_cap_cents = daily_cap_cents
        self.spent_cents = 0

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if amount_cents > self.per_call_cap_cents or self.spent_cents + amount_cents > self.daily_cap_cents:
            raise ValueError("x402 spend cap exceeded")
        raise RuntimeError("PLACEHOLDER: run scripts/verify_x402.py with an explicit testnet credential")


class X402Rail:
    def __init__(self, adapter: MockX402 | X402Testnet | None = None) -> None:
        self.adapter = adapter or MockX402()
        self.mode = self.adapter.mode

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        return self.adapter.pay(amount_cents, idempotency_key)


class NessieRail:
    mode = "nessie-sandbox"

    def __init__(self, bank: object, *, payer_account_id: str, payee_account_id: str) -> None:
        self.bank = bank
        self.payer_account_id = payer_account_id
        self.payee_account_id = payee_account_id

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        if amount_cents <= 0:
            raise ValueError("Nessie payment amount must be positive")
        result = self.bank.transfer(self.payer_account_id, self.payee_account_id, amount_cents, "Agentropolis purchase", idempotency_key)
        transaction_id = str(result.get("_id") or result.get("id") or result.get("transaction_id") or idempotency_key)
        return PaymentReceipt(transaction_id, amount_cents, "nessie-sandbox", transaction_id, self.mode)


class FetRail:
    mode = "fetch-payment-protocol"

    def pay(self, amount_cents: int, idempotency_key: str) -> PaymentReceipt:
        raise RuntimeError("FetRail delegates to the legacy payment protocol; no standalone rail is configured")

