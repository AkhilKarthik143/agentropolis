from __future__ import annotations

from typing import Any

from app.events.schemas import AgentMessage, AgentMessageType, Proposal
from app.finance.ledger import Account

from .base import AgentContext, BaseBusinessAgent


class TreasuryAgent(BaseBusinessAgent):
    role = "treasury"

    def __init__(self, *, business_id: str) -> None:
        super().__init__(business_id=business_id, objective="protect liquidity and minimum reserve", permissions=("read_balance", "check_reserve", "approve_within_policy"))

    def review(self, proposal: Proposal, context: AgentContext) -> dict[str, Any]:
        buyer = context.engine.businesses.get(proposal.business_id)
        amount = proposal.total_cents or ((proposal.quantity or 0) * (proposal.unit_price_cents or 0))
        cash = context.engine.ledger.balance(proposal.business_id, Account.CASH) if buyer else 0
        if buyer is None:
            return {"decision": "REJECT", "reason": "unknown business", "cash_after_purchase_cents": cash - amount}
        if amount > buyer.spend_limit_cents:
            return {"decision": "REJECT", "reason": "spend limit exceeded", "cash_after_purchase_cents": cash - amount}
        if cash - amount < buyer.reserve_cents:
            return {"decision": "REJECT", "reason": "minimum reserve would be breached", "cash_after_purchase_cents": cash - amount}
        if context.engine.approvals.requires_approval(amount):
            return {"decision": "NEEDS_HUMAN", "reason": "amount exceeds autonomous approval threshold", "cash_after_purchase_cents": cash - amount}
        return {"decision": "APPROVE", "reason": "liquidity policy passed", "cash_after_purchase_cents": cash - amount}

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.ACTION_PROPOSAL:
            return
        proposal = Proposal.model_validate(message.payload["proposal"])
        decision = self.review(proposal, context)
        context.emit("TreasuryAgentReview", business_id=self.business_id, deal_id=proposal.deal_id, proposal=proposal, payload={"agent_id": self.agent_id, **decision}, idempotency_key=f"treasury-review:{proposal.idempotency_key}")
        risk = context.registry.by_role(self.business_id, "risk")
        if risk:
            risk_result = risk.review(proposal, context)
            context.emit("RiskAgentReview", business_id=self.business_id, deal_id=proposal.deal_id, proposal=proposal, payload={"agent_id": risk.agent_id, **risk_result}, idempotency_key=f"risk-review:{proposal.idempotency_key}")
            if not risk_result["allowed"]:
                return
        payments = context.registry.by_role(self.business_id, "payments")
        if payments and decision["decision"] != "REJECT":
            payments.handle_message(message, context)

