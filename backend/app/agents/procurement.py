from __future__ import annotations

from app.events.schemas import AgentMessage, AgentMessageType, Proposal
from app.finance.ledger import Account
from .llm_gateway import LLMGateway
from .base import AgentContext, BaseBusinessAgent


class ProcurementAgent(BaseBusinessAgent):
    role = "procurement"

    def __init__(self, *, business_id: str = "unassigned_buyer", objective: str = "source reliable inputs within policy", gateway: LLMGateway | None = None) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("read_inventory", "discover_suppliers", "request_quote", "propose_purchase"))
        self.gateway = gateway or LLMGateway(mode="replay")

    def propose(self, context: dict) -> Proposal:
        return self.gateway.propose(context)

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.TASK_ASSIGNED:
            return
        task = message.payload["task"]
        self.last_task_id = task["task_id"]
        if task["business_id"] != self.business_id or task["assigned_agent_id"] != self.agent_id:
            raise PermissionError("task assignment does not belong to this agent")
        item = str(task["payload"]["item"])
        quantity = int(task["payload"].get("required_quantity", 12))
        if quantity <= 0:
            raise ValueError("required quantity must be positive")
        buyer = context.engine.businesses[self.business_id]
        negotiation_id = message.correlation_id or f"negotiation:{task['task_id']}"
        negotiation = context.registry.by_role(self.business_id, "negotiation")
        if negotiation is None:
            raise RuntimeError("negotiation agent unavailable")
        context.registry.store.update_task(task["task_id"], "running")
        session = context.registry.store.negotiation(negotiation_id)
        if session is None:
            suppliers = []
            excluded = task["payload"].get("excluded_supplier_ids", [])
            broker = context.registry.by_role(self.business_id, "broker")
            candidates = broker.discover(item, context) if broker else context.registry.for_businesses_by_role("supplier")
            for supplier_agent in candidates:
                supplier = context.engine.businesses[supplier_agent.business_id]
                risk = context.registry.risk_review(self.business_id, supplier.business_id, context)
                allowed = getattr(buyer, "allowed_suppliers", [])
                if item not in supplier.categories or supplier.business_id in excluded or (allowed and supplier.business_id not in allowed) or not risk["allowed"]:
                    continue
                if hasattr(context.engine, "_buy_supplier_intelligence"):
                    context.engine._buy_supplier_intelligence(buyer, supplier, negotiation_id)
                suppliers.append(supplier.business_id)
            budget = min(buyer.spend_limit_cents, max(0, context.engine.ledger.balance(self.business_id, Account.CASH) - buyer.reserve_cents))
            session = {"negotiation_id": negotiation_id, "business_id": self.business_id, "task_id": task["task_id"], "item": item, "quantity": quantity, "budget_cents": min(budget, int(task["payload"].get("budget_cents", budget))), "objective": buyer.objective, "deadline_tick": context.engine.clock.tick + 6, "max_rounds": 3, "expected_suppliers": suppliers, "offers": {}, "rounds": {}, "finished_suppliers": [], "status": "negotiating", "recovery": bool(task["payload"].get("recovery")), "created_tick": context.engine.clock.tick}
            context.registry.store.save_negotiation(session)
            self.decisions += 1
        if session["status"] != "negotiating":
            return
        if not session["expected_suppliers"]:
            session.update(status="rejected", reason="no eligible suppliers or available capacity")
            context.registry.store.save_negotiation(session)
            context.registry.store.update_task(task["task_id"], "failed", {"reason": session["reason"]})
            context.emit("NegotiationRejected", business_id=self.business_id, deal_id=negotiation_id, payload={"reason": session["reason"]}, idempotency_key=f"negotiation-rejected:{negotiation_id}")
            return
        for supplier_id in session["expected_suppliers"]:
            payload = {"negotiation_id": negotiation_id, "item": item, "quantity": quantity, "round": 1, "reply_to": negotiation.agent_id, "deadline_tick": session["deadline_tick"]}
            context.send(message_type=AgentMessageType.REQUEST_FOR_QUOTE, sender_id=self.agent_id, recipient_id=f"supplier_agent:{supplier_id}", business_id=self.business_id, correlation_id=negotiation_id, payload=payload, idempotency_key=f"rfq:{negotiation_id}:{supplier_id}")
            context.emit("RFQSent", business_id=self.business_id, deal_id=negotiation_id, payload={"from_agent_id": self.agent_id, "to_agent_id": f"supplier_agent:{supplier_id}", **payload}, idempotency_key=f"rfq-event:{negotiation_id}:{supplier_id}")
        context.registry.store.update_task(task["task_id"], "waiting")
