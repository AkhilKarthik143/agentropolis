"""Business agent registry and typed in-process message router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.events.schemas import AgentMessage

from .base import AgentContext, BaseBusinessAgent
from .transport import InProcessTransport


@dataclass
class AgentRegistry:
    engine: Any
    transport: InProcessTransport = field(default_factory=InProcessTransport)
    agents: dict[str, BaseBusinessAgent] = field(default_factory=dict)

    def register(self, agent: BaseBusinessAgent) -> BaseBusinessAgent:
        if agent.agent_id in self.agents:
            raise ValueError(f"agent already registered: {agent.agent_id}")
        self.agents[agent.agent_id] = agent
        self.engine._emit(
            "AgentRegistered",
            agent.business_id,
            payload=agent.status_snapshot(),
            idempotency_key=f"agent:{agent.agent_id}",
        )
        return agent

    def get(self, agent_id: str) -> BaseBusinessAgent:
        try:
            return self.agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"unknown agent: {agent_id}") from exc

    def for_business(self, business_id: str) -> list[BaseBusinessAgent]:
        return [agent for agent in self.agents.values() if agent.business_id == business_id]

    def by_role(self, business_id: str, role: str) -> BaseBusinessAgent | None:
        return next((agent for agent in self.for_business(business_id) if agent.role == role), None)

    def for_businesses_by_role(self, role: str) -> list[BaseBusinessAgent]:
        return [agent for agent in self.agents.values() if agent.role == role]

    def risk_review(self, buyer_id: str, supplier_id: str, context: AgentContext) -> dict[str, Any]:
        risk = self.by_role(buyer_id, "risk")
        if risk is None:
            return {"allowed": False, "reason": "risk agent unavailable", "supplier_id": supplier_id}
        return risk.review_supplier(supplier_id, context)  # type: ignore[attr-defined]

    def send(self, message: AgentMessage, context: AgentContext) -> bool:
        wire = message.model_dump(mode="json")
        if not self.transport.send(wire):
            return False
        self.engine._emit(
            "AgentMessageSent",
            message.business_id,
            message.correlation_id,
            payload=wire,
            idempotency_key=f"agent-message:{message.idempotency_key}",
        )
        recipient = self.agents.get(message.recipient_id)
        if recipient is None:
            self.engine._emit(
                "AgentMessageUndeliverable",
                message.business_id,
                message.correlation_id,
                payload={"recipient_id": message.recipient_id, "message_id": message.message_id},
                idempotency_key=f"agent-undeliverable:{message.idempotency_key}",
            )
            return False
        recipient.status = "working"
        recipient.handle_message(message, context)
        recipient.status = "idle"
        return True

    def snapshot(self) -> list[dict[str, Any]]:
        return [agent.status_snapshot() for agent in self.agents.values()]
