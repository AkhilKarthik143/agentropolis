"""One worker runtime hosting many business-owned agent teams.

The MVP deliberately uses one process and an idempotent in-process transport.
The message envelope and registry are transport-independent, so selected roles
can later be exposed through Fetch.ai without changing business behavior.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext
from app.agents.inventory_agent import InventoryAgent
from app.agents.manager import ManagerAgent
from app.agents.negotiation import NegotiationAgent
from app.agents.payments import PaymentsAgent
from app.agents.procurement import ProcurementAgent
from app.agents.registry import AgentRegistry
from app.agents.risk import RiskAgent
from app.agents.supplier import SupplierAgent
from app.agents.treasury import TreasuryAgent
from app.economy.engine import EconomyEngine


class AgentRuntime:
    """Schedules agent work while leaving state mutation to ``EconomyEngine``."""

    def __init__(self, engine: EconomyEngine) -> None:
        self.engine = engine
        self.registry = AgentRegistry(engine)
        self._register_teams()

    def _register_teams(self) -> None:
        for business in self.engine.businesses.values():
            self.register_business(business)

    def register_business(self, business: Any) -> None:
        """Create a validated team when a business joins an active simulation."""
        if self.registry.for_business(business.business_id):
            return
        if business.role == "buyer":
            self.registry.register(ManagerAgent(business_id=business.business_id, objective=business.objective))
            self.registry.register(InventoryAgent(business_id=business.business_id, objective=business.objective))
            self.registry.register(ProcurementAgent(business_id=business.business_id, objective=business.objective))
            self.registry.register(NegotiationAgent(business_id=business.business_id, objective=business.objective))
            self.registry.register(TreasuryAgent(business_id=business.business_id))
            self.registry.register(RiskAgent(business_id=business.business_id))
            self.registry.register(PaymentsAgent(business_id=business.business_id))
        elif business.role == "supplier":
            self.registry.register(SupplierAgent(business_id=business.business_id, objective="sell profitably while protecting stock and delivery reliability"))

    def tick(self) -> list[dict[str, Any]]:
        self.engine.clock.advance(ticks=1)
        actions: list[dict[str, Any]] = []
        context = AgentContext(self.engine, self.registry, actions)
        for business in self.engine.businesses.values():
            if business.role != "buyer":
                continue
            inventory = self.registry.by_role(business.business_id, "inventory")
            if not isinstance(inventory, InventoryAgent):
                continue
            signal = inventory.low_stock_signal(self.engine)
            if signal is None:
                continue
            correlation_id = f"need:{business.business_id}:{self.engine.clock.day}:{self.engine.clock.tick}"
            inventory.publish_need(context, signal, correlation_id=correlation_id)
        self.engine._emit("SchedulerTick", payload={"clock": self.engine.clock.now(), "actions": len(actions), "agent_runtime": True})
        return actions

    def snapshot(self) -> dict[str, Any]:
        events = self.engine.bus.replay()
        return {
            "agents": self.registry.snapshot(),
            "tasks": [event.payload.get("task", {}) for event in events if event.type == "AgentTaskAssigned"],
            "messages": [event.payload for event in events if event.type == "AgentMessageSent"],
            "transport": {"mode": "inprocess", "queued_messages": len(self.registry.transport.messages)},
        }
