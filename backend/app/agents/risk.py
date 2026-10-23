from __future__ import annotations

from typing import Any

from app.events.schemas import Proposal, ProposalType
from app.security.gate import inspect_proposal

from .base import BaseBusinessAgent


class RiskAgent(BaseBusinessAgent):
    role = "risk"

    def __init__(self, *, business_id: str) -> None:
        super().__init__(business_id=business_id, objective="reject unreliable or policy-violating counterparties", permissions=("read_credit", "review_counterparty", "escalate"))

    def review_supplier(self, supplier_id: str, context: Any) -> dict[str, Any]:
        supplier = context.engine.businesses.get(supplier_id)
        if supplier is None or not supplier.active:
            return {"allowed": False, "reason": "supplier unavailable", "supplier_id": supplier_id}
        if supplier.supplier_note:
            gate = inspect_proposal(Proposal(
                type=ProposalType.OFFER,
                agent_id=self.agent_id,
                business_id=self.business_id,
                counterparty_id=supplier_id,
                item="policy-check",
                quantity=1,
                unit_price_cents=1,
                total_cents=1,
                metadata={"supplier_note": supplier.supplier_note},
            ))
            if not gate.allowed:
                context.emit(
                    "ACTION_BLOCKED",
                    business_id=self.business_id,
                    payload={"supplier_id": supplier_id, "reason": gate.reason, "code": gate.code, "agent_id": self.agent_id},
                    idempotency_key=f"agent-injection-blocked:{self.business_id}:{supplier_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
                )
        credit = context.engine.credit.check_supplier(supplier_id)
        supplier.credit_status, supplier.credit_score, supplier.credit_reason = credit.status, credit.score, credit.reason
        context.emit("CRS_CHECKED", business_id=self.business_id, payload={"supplier_id": supplier_id, "status": credit.status, "score": credit.score, "reason": credit.reason, "mode": credit.mode}, idempotency_key=f"agent-crs:{self.business_id}:{supplier_id}:{context.engine.clock.day}:{context.engine.clock.tick}")
        if credit.status == "blocked":
            context.emit("SUPPLIER_BLOCKED", business_id=self.business_id, payload={"supplier_id": supplier_id, "reason": credit.reason, "ledger_free": True, "agent_id": self.agent_id}, idempotency_key=f"agent-supplier-blocked:{self.business_id}:{supplier_id}:{context.engine.clock.day}:{context.engine.clock.tick}")
        allowed = credit.status != "blocked" and supplier.reliability >= 0.7
        return {"allowed": allowed, "reason": "counterparty policy passed" if allowed else "credit or reliability policy failed", "supplier_id": supplier_id, "credit_status": credit.status, "reliability": supplier.reliability}

    def review(self, proposal: Proposal, context: Any) -> dict[str, Any]:
        return self.review_supplier(str(proposal.counterparty_id), context)

