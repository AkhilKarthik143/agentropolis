"""Permission-checked durable message router with bounded delivery retries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.events.schemas import AgentMessage
from app.orchestration.store import RuntimeStore
from .base import AgentContext, BaseBusinessAgent
from .transport import InProcessTransport


# Permissions are captured by the registry at registration; agent attributes and
# supplier-controlled message payloads cannot grant authority.
SEND_PERMISSIONS = {
    "INVENTORY_LOW": {"inventory": "publish_need", "recovery": "coordinate_recovery"},
    "TASK_ASSIGNED": {"manager": "assign_tasks", "recovery": "coordinate_recovery"},
    "REQUEST_FOR_QUOTE": {"procurement": "request_quote", "negotiation": "counter_offer"},
    "QUOTE": {"supplier": "quote"},
    "COUNTER_OFFER": {"negotiation": "counter_offer", "supplier": "counter_offer"},
    "ACTION_PROPOSAL": {"procurement": "propose_purchase", "negotiation": "propose_purchase", "treasury": "approve_within_policy"},
    "ACTION_RESULT": {"payments": "submit_approved_payment", "accounting": "review_books", "accounts_payable": "review_invoices", "controller": "review_exceptions"},
    "RECOVERY_REQUESTED": {"recovery": "coordinate_recovery", "controller": "review_exceptions", "inventory": "confirm_receipt"},
    "ACK": {},
}
RECEIVE_ROLES = {
    "INVENTORY_LOW": {"manager"}, "TASK_ASSIGNED": {"procurement"},
    "REQUEST_FOR_QUOTE": {"supplier"}, "QUOTE": {"negotiation"},
    "COUNTER_OFFER": {"supplier", "negotiation"},
    "ACTION_PROPOSAL": {"treasury", "payments"},
    "ACTION_RESULT": {"manager", "controller", "accounting", "accounts_payable", "recovery"},
    "RECOVERY_REQUESTED": {"recovery", "manager"},
    "ACK": set(),
}
CROSS_BUSINESS = {"REQUEST_FOR_QUOTE", "QUOTE", "COUNTER_OFFER"}


@dataclass
class AgentRegistry:
    engine: Any
    transport: InProcessTransport = field(default_factory=InProcessTransport)
    agents: dict[str, BaseBusinessAgent] = field(default_factory=dict)
    store: RuntimeStore | None = None
    _permissions: dict[str, frozenset[str]] = field(default_factory=dict)
    active_agent_id: str | None = None

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = RuntimeStore(self.engine.session_id, getattr(self.engine.bus.store, "path", None))

    @property
    def tick(self) -> int:
        return int(self.engine.clock.tick)

    def register(self, agent: BaseBusinessAgent) -> BaseBusinessAgent:
        if agent.agent_id in self.agents:
            return self.agents[agent.agent_id]
        self.agents[agent.agent_id] = agent
        self._permissions[agent.agent_id] = frozenset(agent.permissions)
        previous = self.store.agent(agent.agent_id)
        if previous:
            agent.last_task_id = previous.get("last_task_id")
            agent.handled_messages = previous.get("handled_messages", 0)
            agent.decisions = previous.get("decisions", 0)
        self.store.save_agent(agent.status_snapshot())
        self.engine._emit("AgentRegistered", agent.business_id, payload=agent.status_snapshot(), idempotency_key=f"agent:{agent.agent_id}")
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

    def require(self, agent_id: str, permission: str, business_id: str | None = None) -> None:
        agent = self.get(agent_id)
        if self.active_agent_id is not None and self.active_agent_id != agent_id:
            raise PermissionError("an agent cannot impersonate another role")
        if permission not in self._permissions[agent_id]:
            raise PermissionError(f"{agent.role} cannot use {permission}")
        if business_id is not None and agent.business_id != business_id:
            raise PermissionError("an agent cannot act for another business")

    def risk_review(self, buyer_id: str, supplier_id: str, context: AgentContext) -> dict[str, Any]:
        risk = self.by_role(buyer_id, "risk")
        if risk is None:
            return {"allowed": False, "reason": "risk agent unavailable", "supplier_id": supplier_id}
        return risk.review_supplier(supplier_id, context)

    def validate_message(self, message: AgentMessage) -> None:
        if message.simulation_id != self.engine.session_id:
            raise PermissionError("cross-simulation message rejected")
        sender = self.get(message.sender_id)
        recipient = self.get(message.recipient_id)
        kind = message.message_type.value
        permission = SEND_PERMISSIONS.get(kind, {}).get(sender.role)
        if permission is None or recipient.role not in RECEIVE_ROLES.get(kind, set()):
            raise PermissionError(f"{sender.role} cannot send {kind} to {recipient.role}")
        self.require(sender.agent_id, permission)
        if sender.business_id != recipient.business_id and kind not in CROSS_BUSINESS:
            raise PermissionError("cross-business authority rejected")
        # The envelope's business is the buyer for inter-business RFQ traffic.
        owner = recipient.business_id if sender.role == "supplier" else sender.business_id
        if message.business_id != owner:
            raise PermissionError("message business does not match workflow owner")

    def send(self, message: AgentMessage, context: AgentContext, *, ttl: int = 12) -> bool:
        self.validate_message(message)
        if not self.store.enqueue(message, tick=self.tick, ttl=ttl):
            return False
        wire = message.model_dump(mode="json")
        self.transport.send(wire)
        self.engine._emit("AgentMessageSent", message.business_id, message.correlation_id, payload=wire, idempotency_key=f"agent-message:{message.idempotency_key}")
        return True

    def drain(self, context: AgentContext, *, limit: int = 256) -> int:
        for row in self.store.expire(self.tick):
            message = row["message"]
            self.engine._emit("AgentMessageExpired", message["business_id"], message.get("correlation_id"), payload={"message_id": message["message_id"], "reason": "delivery deadline exceeded"}, idempotency_key=f"expired:{message['message_id']}")
        delivered = 0
        for _ in range(limit):
            row = self.store.claim(self.tick)
            if row is None:
                break
            message = AgentMessage.model_validate(row["message"])
            recipient = self.agents.get(message.recipient_id)
            try:
                # Recheck permissions after recovery; persisted messages do not
                # bypass a changed deployment policy.
                self.validate_message(message)
                if recipient is None:
                    raise KeyError("recipient unavailable")
                recipient.status = "working"
                self.active_agent_id = recipient.agent_id
                recipient.handle_message(message, context)
                self.store.acknowledge(message.message_id)
                delivered += 1
                self.engine._emit("AgentMessageAcknowledged", message.business_id, message.correlation_id, payload={"message_id": message.message_id, "recipient_id": message.recipient_id, "attempts": row["attempts"], "economic_success": False}, idempotency_key=f"ack:{message.message_id}")
            except Exception as exc:
                status = self.store.fail(message.message_id, tick=self.tick, error=f"{type(exc).__name__}: {exc}")
                if recipient:
                    recipient.status = "failed" if status == "dead_letter" else "retrying"
                self.engine._emit("AgentMessageFailed", message.business_id, message.correlation_id, payload={"message_id": message.message_id, "status": status, "attempts": row["attempts"], "error_type": type(exc).__name__}, idempotency_key=f"delivery-error:{message.message_id}:{row['attempts']}")
                if status == "dead_letter" and message.payload.get("task"):
                    self.store.update_task(message.payload["task"]["task_id"], "failed", {"reason": "message delivery exhausted retries"})
            finally:
                self.active_agent_id = None
                if recipient:
                    if recipient.status == "working":
                        recipient.status = "idle"
                    self.store.save_agent(recipient.status_snapshot())
        return delivered

    def snapshot(self) -> list[dict[str, Any]]:
        return [agent.status_snapshot() for agent in self.agents.values()]
