from __future__ import annotations

from dataclasses import dataclass

from app.economy.engine import EconomyEngine
from app.events.schemas import Proposal
from app.finance.ledger import Account


@dataclass(frozen=True)
class TreasuryRiskDecision:
    decision: str
    reason: str
    cash_after_purchase_cents: int


class TreasuryRiskAgent:
    """Policy recommender; it never writes to the economy engine."""

    role = "treasury_risk"

    def review(self, engine: EconomyEngine, proposal: Proposal) -> TreasuryRiskDecision:
        buyer = engine.businesses.get(proposal.business_id)
        if buyer is None:
            return TreasuryRiskDecision("REJECT", "unknown proposing business", 0)
        amount = proposal.total_cents or ((proposal.quantity or 0) * (proposal.unit_price_cents or 0))
        cash = engine.ledger.balance(proposal.business_id, Account.CASH)
        after = cash - amount
        if after < buyer.reserve_cents:
            return TreasuryRiskDecision("REJECT", "minimum cash reserve would be breached", after)
        supplier = engine.businesses.get(proposal.counterparty_id or "")
        if supplier is None or not supplier.active or supplier.reliability < 0.35:
            return TreasuryRiskDecision("REJECT", "supplier is unavailable or below reliability policy", after)
        if engine.approvals.requires_approval(amount):
            return TreasuryRiskDecision("NEEDS_HUMAN", "purchase exceeds autonomous approval threshold", after)
        return TreasuryRiskDecision("APPROVE", "reserve, spend, and reliability checks passed", after)
