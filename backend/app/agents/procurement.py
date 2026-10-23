from __future__ import annotations

from dataclasses import dataclass

from app.events.schemas import AgentMessage, AgentMessageType, Proposal, ProposalType
from .llm_gateway import LLMGateway
from .base import AgentContext, BaseBusinessAgent
from .supplier import SupplierQuote


class ProcurementAgent(BaseBusinessAgent):
    role = "procurement"

    def __init__(self, *, business_id: str = "unassigned_buyer", objective: str = "source reliable inputs within policy", gateway: LLMGateway | None = None) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("read_inventory", "discover_suppliers", "request_quote", "propose_purchase"))
        self.gateway = gateway or LLMGateway()

    def propose(self, context: dict) -> Proposal:
        """Return only a validated proposal; no engine mutation happens here."""
        return self.gateway.propose(context)

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.TASK_ASSIGNED:
            return
        task = message.payload["task"]
        item = str(task["payload"]["item"])
        quantity = int(task["payload"].get("required_quantity", 12))
        self.status = "working"
        suppliers = context.registry.for_businesses_by_role("supplier")
        quotes: list[SupplierQuote] = []
        for supplier_agent in suppliers:
            supplier = context.engine.businesses[supplier_agent.business_id]
            risk = context.registry.risk_review(self.business_id, supplier_agent.business_id, context)
            if not risk["allowed"]:
                continue
            intelligence = context.engine._buy_supplier_intelligence(
                context.engine.businesses[self.business_id],
                supplier,
                f"{context.engine.clock.day}:{context.engine.clock.tick}",
            )
            quote = supplier_agent.quote(supplier, item=item, quantity=quantity)
            if quote is None:
                continue
            quotes.append(quote)
            context.emit(
                "RFQSent",
                business_id=self.business_id,
                payload={"from_agent_id": self.agent_id, "to_agent_id": supplier_agent.agent_id, "item": item, "quantity": quantity},
                idempotency_key=f"rfq:{self.business_id}:{supplier_agent.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
            )
            context.emit(
                "OfferReceived",
                business_id=self.business_id,
                payload={"supplier_agent_id": supplier_agent.agent_id, "quote": quote.as_dict(), "risk": risk, "reliability_report": intelligence},
                idempotency_key=f"offer:{self.business_id}:{supplier_agent.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
            )
        negotiation = context.registry.by_role(self.business_id, "negotiation")
        result = negotiation.select(quotes, context) if negotiation else None
        if result is None:
            self.status = "idle"
            return
        quote = result.quote
        proposal = Proposal(
            type=ProposalType.OFFER,
            proposal_id=f"agent-proposal-{self.business_id}-{context.engine.clock.day}-{context.engine.clock.tick}",
            idempotency_key=f"agent-proposal:{self.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
            agent_id=self.agent_id,
            business_id=self.business_id,
            counterparty_id=quote.supplier_id,
            deal_id=f"agent-deal:{self.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
            item=item,
            quantity=quantity,
            unit="units",
            unit_price_cents=quote.unit_price_cents,
            total_cents=quote.total_cents,
            delivery_days=quote.delivery_days,
            payment_terms="on receipt",
            public_rationale=f"{quote.supplier_name} won an independent team negotiation on reliability, price, and delivery.",
            private_rationale=result.rationale,
            metadata={"agent_team": True, "delivery_mode": "on_receipt", "roles": {"requester": self.agent_id, "approver": f"treasury_agent:{self.business_id}", "payer": f"payments_agent:{self.business_id}", "poster": f"accountant_agent:{self.business_id}"}},
        )
        treasury = context.registry.by_role(self.business_id, "treasury")
        if treasury:
            context.send(
                message_type=AgentMessageType.ACTION_PROPOSAL,
                sender_id=self.agent_id,
                recipient_id=treasury.agent_id,
                business_id=self.business_id,
                correlation_id=proposal.deal_id,
                payload={"proposal": proposal.model_dump(by_alias=True)},
                idempotency_key=f"proposal-message:{proposal.idempotency_key}",
            )
        self.status = "idle"

