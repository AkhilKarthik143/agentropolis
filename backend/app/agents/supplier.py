"""Seller-owned quote policy; no central planner chooses a supplier's price."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.events.schemas import AgentMessage, AgentMessageType
from app.finance.ledger import Account
from .base import BaseBusinessAgent, AgentContext


@dataclass(frozen=True)
class SupplierProfile:
    supplier_id: str
    inventory: int
    unit_price_cents: int
    delivery_days: int
    reliability: float
    bankrupt: bool = False
    negotiation_style: str = "steady"


@dataclass(frozen=True)
class SupplierQuote:
    supplier_id: str
    supplier_name: str
    item: str
    quantity: int
    unit_price_cents: int
    delivery_days: int
    reliability: float
    negotiation_style: str = "state_based"
    available_quantity: int = 0

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents

    def with_price(self, unit_price_cents: int) -> "SupplierQuote":
        return replace(self, unit_price_cents=unit_price_cents)

    def as_dict(self) -> dict[str, Any]:
        return {"supplier_id": self.supplier_id, "supplier_name": self.supplier_name, "item": self.item, "quantity": self.quantity, "unit_price_cents": self.unit_price_cents, "total_cents": self.total_cents, "delivery_days": self.delivery_days, "reliability": self.reliability, "negotiation_style": self.negotiation_style, "available_quantity": self.available_quantity}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SupplierQuote":
        return cls(**{key: value[key] for key in cls.__dataclass_fields__ if key in value})


class SupplierAgent(BaseBusinessAgent):
    role = "supplier"

    def __init__(self, *, business_id: str | None = None, objective: str = "sell profitably while protecting capacity", profile: SupplierProfile | None = None) -> None:
        super().__init__(business_id=business_id or (profile.supplier_id if profile else "unassigned_supplier"), objective=objective, permissions=("read_capacity", "quote", "counter_offer"))
        self.profile = profile

    @property
    def available(self) -> bool:
        return bool(self.profile and not self.profile.bankrupt and self.profile.inventory > 0)

    def _terms(self, business: Any, item: str, quantity: int, *, cash_cents: int | None = None) -> dict[str, int] | None:
        if not business.active or quantity <= 0 or item not in business.categories:
            return None
        inventory = business.inventory
        available = inventory.available(item) if hasattr(inventory, "available") and item in inventory.quantities else int(business.capacity.get(item, 0))
        if quantity > available:
            return None
        catalog = getattr(business, "catalog", {}).get(item, {})
        cost = max(1, int(catalog.get("cost_price_cents", 3000)))
        list_price = max(cost, int(catalog.get("unit_price_cents", 4000)))
        # Lower remaining capacity raises the supplier's own opportunity cost.
        utilization = quantity / max(available, 1)
        scarcity_premium = int(list_price * max(0, utilization - 0.25) * 0.25)
        margin = max(1, cost // 20)
        floor = cost + margin
        liquidity_discount = int((list_price - floor) * 0.15) if cash_cents is not None and cash_cents < business.reserve_cents * 2 else 0
        price = max(floor, list_price + scarcity_premium - liquidity_discount)
        lead_days = max(0, int(catalog.get("lead_days", 2))) + (1 if utilization > 0.75 else 0)
        return {"available": available, "price": price, "floor": floor, "lead_days": lead_days}

    def quote(self, business: Any, *, item: str, quantity: int, cash_cents: int | None = None) -> SupplierQuote | None:
        terms = self._terms(business, item, quantity, cash_cents=cash_cents)
        if terms is None:
            return None
        self.decisions += 1
        return SupplierQuote(business.business_id, business.name, item, quantity, terms["price"], terms["lead_days"], business.reliability, "state_based", terms["available"])

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type not in {AgentMessageType.REQUEST_FOR_QUOTE, AgentMessageType.COUNTER_OFFER}:
            return
        payload = message.payload
        business = context.engine.businesses[self.business_id]
        item, quantity = str(payload["item"]), int(payload["quantity"])
        round_number = int(payload.get("round", 1))
        if round_number < 1 or round_number > 4:
            raise ValueError("negotiation round outside authority")
        if int(payload.get("deadline_tick", context.engine.clock.tick)) < context.engine.clock.tick:
            return
        negotiation_id = str(payload["negotiation_id"])
        memory_key = f"negotiation:{negotiation_id}"
        previous = context.recall(self.agent_id, memory_key, {})
        # Re-send the previously decided response if delivery crashed after the
        # private state was committed but before its durable outbox was written.
        cached = previous.get("responses", {}).get(str(round_number))
        if cached is None:
            cash = context.engine.ledger.balance(self.business_id, Account.CASH)
            quote = self.quote(business, item=item, quantity=quantity, cash_cents=cash)
            terms = self._terms(business, item, quantity, cash_cents=cash)
            status, reason = "offered", "price reflects current cost, available stock, and liquidity"
            if quote is None:
                status, reason = "rejected", "supplier inactive, item unsupported, or insufficient unreserved stock"
            elif message.message_type is AgentMessageType.COUNTER_OFFER:
                offered_price = int(payload["unit_price_cents"])
                if offered_price <= 0:
                    raise ValueError("counter price must be positive")
                # The seller decides whether to accept, counter, or refuse. The
                # buyer never edits a seller quote in place.
                previous_price = int(previous.get("last_price", quote.unit_price_cents))
                if offered_price >= max(terms["floor"], previous_price - max(1, (previous_price - terms["floor"]) // 3)):
                    quote = quote.with_price(max(terms["floor"], min(offered_price, quote.unit_price_cents)))
                    status, reason = "accepted", "counteroffer meets the seller's current margin and capacity constraints"
                elif round_number >= 3 and offered_price < terms["floor"]:
                    quote, status, reason = None, "rejected", "counteroffer remains below the seller's cost and minimum margin"
                else:
                    next_price = max(terms["floor"], (previous_price + max(terms["floor"], offered_price)) // 2)
                    quote = quote.with_price(next_price)
                    status, reason = "countered", "seller narrowed the price gap without crossing its cost floor"
            cached = {"negotiation_id": negotiation_id, "supplier_id": self.business_id, "round": round_number, "status": status, "reason": reason, "quote": quote.as_dict() if quote else None, "decision_source": "deterministic_policy", "deadline_tick": payload.get("deadline_tick")}
            responses = previous.get("responses", {})
            responses[str(round_number)] = cached
            context.remember(self.agent_id, memory_key, {"buyer_id": message.business_id, "responses": responses, "last_price": quote.unit_price_cents if quote else previous.get("last_price"), "floor_cents": terms["floor"] if terms else None})
        recipient_id = str(payload.get("reply_to", f"negotiation_agent:{message.business_id}"))
        context.emit("QuoteCreated" if round_number == 1 else "SupplierCounterOffer", business_id=message.business_id, deal_id=negotiation_id, payload={"supplier_agent_id": self.agent_id, **cached}, idempotency_key=f"supplier-decision:{negotiation_id}:{self.business_id}:{round_number}")
        context.send(message_type=AgentMessageType.QUOTE, sender_id=self.agent_id, recipient_id=recipient_id, business_id=message.business_id, correlation_id=negotiation_id, payload=cached, idempotency_key=f"quote:{negotiation_id}:{self.business_id}:{round_number}")
