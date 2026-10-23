"""Deterministic treasury recommendations used before engine execution."""

from __future__ import annotations

from dataclasses import dataclass

from .ledger import Account, Ledger


@dataclass(frozen=True)
class LiquidityDecision:
    business_id: str
    cash_cents: int
    amount_cents: int
    reserve_cents: int
    cash_after_cents: int
    decision: str
    reason: str


class TreasuryService:
    role = "treasury_service"

    def evaluate(self, ledger: Ledger, business_id: str, amount_cents: int, reserve_cents: int, *, spend_limit_cents: int | None = None, approval_threshold_cents: int | None = None) -> LiquidityDecision:
        cash = ledger.balance(business_id, Account.CASH)
        after = cash - amount_cents
        if amount_cents <= 0:
            return LiquidityDecision(business_id, cash, amount_cents, reserve_cents, after, "REJECT", "amount must be positive")
        if after < reserve_cents:
            return LiquidityDecision(business_id, cash, amount_cents, reserve_cents, after, "REJECT", "minimum reserve would be breached")
        if spend_limit_cents is not None and amount_cents > spend_limit_cents:
            return LiquidityDecision(business_id, cash, amount_cents, reserve_cents, after, "REJECT", "spend limit exceeded")
        if approval_threshold_cents is not None and amount_cents >= approval_threshold_cents:
            return LiquidityDecision(business_id, cash, amount_cents, reserve_cents, after, "NEEDS_HUMAN", "amount crosses autonomous approval threshold")
        return LiquidityDecision(business_id, cash, amount_cents, reserve_cents, after, "APPROVE", "liquidity policy passed")
