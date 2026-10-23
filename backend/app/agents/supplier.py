from __future__ import annotations

from dataclasses import dataclass, replace

from typing import Any

from app.events.schemas import AgentMessage, AgentMessageType

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
    negotiation_style: str
    available_quantity: int

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents

    def with_price(self, unit_price_cents: int) -> "SupplierQuote":
        return replace(self, unit_price_cents=unit_price_cents)

    def as_dict(self) -> dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "item": self.item,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "total_cents": self.total_cents,
            "delivery_days": self.delivery_days,
            "reliability": self.reliability,
            "negotiation_style": self.negotiation_style,
            "available_quantity": self.available_quantity,
        }


class SupplierAgent(BaseBusinessAgent):
    role = "supplier"

    def __init__(self, *, business_id: str | None = None, objective: str = "sell profitably while protecting capacity", profile: SupplierProfile | None = None) -> None:
        if business_id is None and profile is not None:
            business_id = profile.supplier_id
        if business_id is None:
            business_id = "unassigned_supplier"
        super().__init__(business_id=business_id, objective=objective, permissions=("read_capacity", "quote", "counter_offer", "reserve_stock"))
        self.profile = profile

    @property
    def available(self) -> bool:
        return bool(self.profile and not self.profile.bankrupt and self.profile.inventory > 0)

    def quote(self, business: Any, *, item: str, quantity: int) -> SupplierQuote | None:
        if not business.active or item not in business.categories:
            return None
        available = int(business.capacity.get(item, 100)) if getattr(business, "capacity", None) else 100
        if available < quantity:
            return None
        base_price = {"reliable": 4200, "cheap": 3700, "flexible": 3950}.get(business.negotiation_style, 4100)
        delivery_days = 1 if business.negotiation_style == "flexible" else 2
        self.decisions += 1
        return SupplierQuote(
            supplier_id=business.business_id,
            supplier_name=business.name,
            item=item,
            quantity=quantity,
            unit_price_cents=base_price,
            delivery_days=delivery_days,
            reliability=business.reliability,
            negotiation_style=business.negotiation_style,
            available_quantity=available,
        )

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.REQUEST_FOR_QUOTE:
            return
        business = context.engine.businesses[self.business_id]
        quote = self.quote(business, item=str(message.payload["item"]), quantity=int(message.payload["quantity"]))
        if quote is None:
            return
        context.emit(
            "QuoteCreated",
            business_id=message.business_id,
            deal_id=message.correlation_id,
            payload={"supplier_agent_id": self.agent_id, "quote": quote.as_dict()},
            idempotency_key=f"quote:{message.idempotency_key}:{self.agent_id}",
        )

