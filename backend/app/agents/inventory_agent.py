from __future__ import annotations

from typing import Any

from .base import AgentContext, BaseBusinessAgent
from app.events.schemas import AgentMessage, AgentMessageType


class InventoryAgent(BaseBusinessAgent):
    """Detects shortages and confirms physical receipt of goods."""

    role = "inventory"

    def __init__(self, *, business_id: str, objective: str) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("read_inventory", "publish_need", "confirm_receipt"))

    def low_stock_signal(self, engine: Any) -> dict[str, Any] | None:
        business = engine.businesses[self.business_id]
        quantity = business.inventory.quantity(business.inventory_item)
        if quantity > business.low_stock_threshold:
            return None
        return {
            "item": business.inventory_item,
            "quantity_on_hand": quantity,
            "threshold": business.low_stock_threshold,
            "required_quantity": max(12, business.low_stock_threshold * 2 - quantity),
            "trigger": "sim_clock",
        }

    def publish_need(self, context: AgentContext, signal: dict[str, Any], *, correlation_id: str) -> None:
        context.emit(
            "NeedDetected",
            business_id=self.business_id,
            payload={**signal, "agent_id": self.agent_id},
            idempotency_key=f"need:{self.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
        )
        manager = context.registry.by_role(self.business_id, "manager")
        if manager:
            context.send(
                message_type=AgentMessageType.INVENTORY_LOW,
                sender_id=self.agent_id,
                recipient_id=manager.agent_id,
                business_id=self.business_id,
                correlation_id=correlation_id,
                payload=signal,
                idempotency_key=f"inventory-low:{self.business_id}:{context.engine.clock.day}:{context.engine.clock.tick}",
            )

    def confirm_receipt(self, context: AgentContext, deal_id: str, item: str, quantity: int) -> None:
        context.emit(
            "InventoryReceiptConfirmed",
            business_id=self.business_id,
            deal_id=deal_id,
            payload={"item": item, "quantity": quantity, "agent_id": self.agent_id},
            idempotency_key=f"receipt-confirmed:{deal_id}",
        )
