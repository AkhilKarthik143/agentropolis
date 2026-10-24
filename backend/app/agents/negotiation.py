"""Buyer-owned negotiation state and independently delivered supplier replies."""
from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentContext, BaseBusinessAgent
from app.agents.llm_gateway import LLMGateway
from app.agents.supplier import SupplierQuote
from app.events.schemas import AgentMessage, AgentMessageType, Proposal, ProposalType


@dataclass(frozen=True)
class NegotiationResult:
    quote: SupplierQuote
    countered: bool
    rationale: str


class NegotiationAgent(BaseBusinessAgent):
    role = "negotiation"

    def __init__(self, *, business_id: str, objective: str, gateway: LLMGateway | None = None) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("read_quotes", "counter_offer", "propose_purchase"))
        self.gateway = gateway or LLMGateway(mode="replay")

    def select(self, quotes: list[SupplierQuote], context: AgentContext) -> NegotiationResult | None:
        buyer = context.engine.businesses[self.business_id]
        viable = [quote for quote in quotes if quote.reliability >= getattr(buyer, "required_reliability", .7) and quote.total_cents <= buyer.spend_limit_cents and quote.available_quantity >= quote.quantity]
        if not viable:
            return None
        objective = buyer.objective.lower()
        if any(word in objective for word in ("cheapest", "lowest cost", "minimize cost")):
            viable.sort(key=lambda quote: (quote.unit_price_cents, -quote.reliability, quote.delivery_days))
        elif any(word in objective for word in ("urgent", "fastest", "speed")):
            viable.sort(key=lambda quote: (quote.delivery_days, -quote.reliability, quote.unit_price_cents))
        else:
            viable.sort(key=lambda quote: (-quote.reliability, quote.unit_price_cents, quote.delivery_days))
        winner = viable[0]
        rationale = f"Current objective '{buyer.objective}' ranked {len(viable)} feasible supplier offers."
        if self.gateway.mode in {"live", "record"}:
            decision = self.gateway.compare_offers({"objective": buyer.objective, "offers": [{**quote.as_dict(), "price_cents": quote.total_cents} for quote in viable]})
            if not decision.selected_supplier_id:
                return None
            winner = next((quote for quote in viable if quote.supplier_id == decision.selected_supplier_id), winner)
            rationale = decision.rationale
        self.decisions += 1
        return NegotiationResult(winner, True, rationale)

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.QUOTE:
            return
        value = message.payload
        session = context.registry.store.negotiation(str(value["negotiation_id"]))
        if session is None or session["business_id"] != self.business_id:
            raise ValueError("unknown negotiation")
        if session["status"] != "negotiating":
            return
        if session["deadline_tick"] < context.engine.clock.tick:
            self.expire(session, context)
            return
        supplier_id = str(value["supplier_id"])
        if supplier_id not in session["expected_suppliers"] or message.sender_id != f"supplier_agent:{supplier_id}":
            raise PermissionError("unsolicited or impersonated supplier offer")
        round_number = int(value["round"])
        previous_round = session["rounds"].get(supplier_id, 0)
        if round_number < previous_round:
            return
        quote = SupplierQuote.from_dict(value["quote"]) if value.get("quote") else None
        if quote and (quote.supplier_id != supplier_id or quote.quantity != session["quantity"] or quote.item != session["item"] or quote.unit_price_cents <= 0):
            raise ValueError("quote changed requested identity, quantity, item, or price bounds")
        session["rounds"][supplier_id] = round_number
        if quote:
            session["offers"][supplier_id] = quote.as_dict()
        else:
            session["offers"].pop(supplier_id, None)
        context.emit("OfferReceived", business_id=self.business_id, deal_id=session["negotiation_id"], payload={"supplier_agent_id": message.sender_id, **value}, idempotency_key=f"offer-received:{session['negotiation_id']}:{supplier_id}:{round_number}")
        finished = value.get("status") in {"rejected", "accepted"} or round_number >= session["max_rounds"]
        if finished:
            if supplier_id not in session["finished_suppliers"]:
                session["finished_suppliers"].append(supplier_id)
        context.registry.store.save_negotiation(session)
        if not finished and quote:
            unit_budget = session["budget_cents"] // session["quantity"]
            desired = max(1, min(unit_budget, int(quote.unit_price_cents * (.90 if round_number == 1 else .97))))
            source = "deterministic_policy"
            if self.gateway.mode in {"live", "record"}:
                decision = self.gateway.negotiate_counter({"supplier_id": supplier_id, "seller_price_cents": quote.unit_price_cents, "buyer_limit_cents": desired, "objective": session["objective"]})
                desired = max(1, min(unit_budget, quote.unit_price_cents, decision.unit_price_cents))
                source = getattr(self.gateway, "last_decision_source", "unknown")
            payload = {"negotiation_id": session["negotiation_id"], "item": session["item"], "quantity": session["quantity"], "unit_price_cents": desired, "round": round_number + 1, "deadline_tick": session["deadline_tick"], "reply_to": self.agent_id}
            context.send(message_type=AgentMessageType.COUNTER_OFFER, sender_id=self.agent_id, recipient_id=message.sender_id, business_id=self.business_id, correlation_id=session["negotiation_id"], payload=payload, idempotency_key=f"counter:{session['negotiation_id']}:{supplier_id}:{round_number + 1}")
            context.emit("CounterOfferSent", business_id=self.business_id, deal_id=session["negotiation_id"], payload={"supplier_id": supplier_id, "agent_id": self.agent_id, "decision_source": source, **payload}, idempotency_key=f"counter-event:{session['negotiation_id']}:{supplier_id}:{round_number + 1}")
        if set(session["finished_suppliers"]) == set(session["expected_suppliers"]):
            self.conclude(session, context)

    def conclude(self, session: dict, context: AgentContext) -> None:
        quotes = [SupplierQuote.from_dict(value) for value in session["offers"].values() if value["total_cents"] <= session["budget_cents"]]
        result = self.select(quotes, context)
        if result is None:
            session.update(status="rejected", reason="all offers failed budget, reliability, stock, or decision policy")
            context.registry.store.save_negotiation(session)
            context.registry.store.update_task(session["task_id"], "failed", {"reason": session["reason"]})
            context.emit("NegotiationRejected", business_id=self.business_id, deal_id=session["negotiation_id"], payload={"reason": session["reason"]}, idempotency_key=f"negotiation-rejected:{session['negotiation_id']}")
            return
        quote = result.quote
        proposal = Proposal(type=ProposalType.OFFER, proposal_id=f"proposal:{session['negotiation_id']}", idempotency_key=f"proposal:{session['negotiation_id']}", agent_id=self.agent_id, business_id=self.business_id, counterparty_id=quote.supplier_id, deal_id=f"deal:{session['negotiation_id']}", item=quote.item, quantity=quote.quantity, unit=context.engine.businesses[quote.supplier_id].catalog.get(quote.item, {}).get("unit", "unit"), unit_price_cents=quote.unit_price_cents, total_cents=quote.total_cents, delivery_days=quote.delivery_days, payment_terms="on receipt", public_rationale=result.rationale, private_rationale="Only independently issued supplier quotes within the current business policy can be submitted.", metadata={"agent_team": True, "delivery_mode": "on_receipt", "negotiation_id": session["negotiation_id"], "task_id": session["task_id"], "recovery": session.get("recovery", False), "roles": {"requester": self.agent_id, "approver": f"treasury_agent:{self.business_id}", "payer": f"payments_agent:{self.business_id}", "poster": f"accounting_agent:{self.business_id}"}})
        treasury = context.registry.by_role(self.business_id, "treasury")
        if treasury is None:
            raise RuntimeError("treasury agent unavailable")
        # Queue before marking terminal: retries always recreate the same outbox
        # key, preventing a crash from losing the final proposal.
        context.send(message_type=AgentMessageType.ACTION_PROPOSAL, sender_id=self.agent_id, recipient_id=treasury.agent_id, business_id=self.business_id, correlation_id=session["negotiation_id"], payload={"proposal": proposal.model_dump(mode="json", by_alias=True), "task_id": session["task_id"]}, idempotency_key=f"proposal-message:{session['negotiation_id']}")
        session.update(status="agreement_proposed", selected_supplier_id=quote.supplier_id, proposal=proposal.model_dump(mode="json", by_alias=True), reason=result.rationale)
        context.registry.store.save_negotiation(session)
        context.emit("NegotiationAgreementProposed", business_id=self.business_id, deal_id=session["negotiation_id"], proposal=proposal, payload={"rounds": session["rounds"], "supplier_id": quote.supplier_id}, idempotency_key=f"agreement:{session['negotiation_id']}")

    def expire(self, session: dict, context: AgentContext) -> None:
        session.update(status="expired", reason="negotiation deadline elapsed before all counterparties completed")
        context.registry.store.save_negotiation(session)
        context.registry.store.update_task(session["task_id"], "failed", {"reason": session["reason"]})
        context.emit("NegotiationExpired", business_id=self.business_id, deal_id=session["negotiation_id"], payload={"deadline_tick": session["deadline_tick"], "received_suppliers": list(session["offers"])}, idempotency_key=f"negotiation-expired:{session['negotiation_id']}")
