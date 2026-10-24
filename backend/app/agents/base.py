"""Shared contracts for business-owned Agentropolis agents.

Agents communicate with typed messages and return recommendations.  They do not
own the economy's mutable state; ``EconomyEngine`` remains the trusted command
handler for money, contracts, inventory, and accounting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.events.schemas import AgentMessage, AgentMessageType, AgentTask, Proposal

if TYPE_CHECKING:
    from app.economy.engine import EconomyEngine
    from .registry import AgentRegistry


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    business_id: str
    role: str


@dataclass
class AgentContext:
    """Narrow runtime capability object passed to agents."""

    engine: "EconomyEngine"
    registry: "AgentRegistry"
    actions: list[dict[str, Any]] = field(default_factory=list)

    def send(
        self,
        *,
        message_type: AgentMessageType | str,
        sender_id: str,
        recipient_id: str,
        business_id: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
        ttl: int = 12,
    ) -> bool:
        message = AgentMessage(
            message_type=message_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            business_id=business_id,
            simulation_id=self.engine.session_id,
            correlation_id=correlation_id,
            payload=payload,
            idempotency_key=idempotency_key or f"msg:{uuid4().hex}",
        )
        return self.registry.send(message, self, ttl=ttl)

    def emit(self, event_type: str, *, business_id: str | None = None, deal_id: str | None = None, proposal: Proposal | None = None, payload: dict[str, Any] | None = None, idempotency_key: str | None = None) -> None:
        self.engine._emit(event_type, business_id, deal_id, proposal=proposal, payload=payload, idempotency_key=idempotency_key)

    def record_action(self, action: dict[str, Any]) -> None:
        self.actions.append(action)

    def require(self, agent_id: str, permission: str, business_id: str | None = None) -> None:
        self.registry.require(agent_id, permission, business_id)

    def submit_purchase(self, agent_id: str, proposal: Proposal) -> Any:
        self.require(agent_id, "submit_approved_payment", proposal.business_id)
        return self.engine.submit_proposal(proposal.model_copy(update={"agent_id":agent_id}))

    def remember(self, agent_id: str, key: str, value: Any) -> None:
        if self.registry.active_agent_id not in {None, agent_id}:
            raise PermissionError("private memory belongs to another agent")
        self.registry.store.remember(agent_id, key, value)

    def recall(self, agent_id: str, key: str, default: Any = None) -> Any:
        if self.registry.active_agent_id not in {None, agent_id}:
            raise PermissionError("private memory belongs to another agent")
        return self.registry.store.recall(agent_id, key, default)


class BaseBusinessAgent:
    """Common lifecycle and status behavior for every business role."""

    role = "agent"

    def __init__(self, *, business_id: str, agent_id: str | None = None, objective: str = "", permissions: tuple[str, ...] = ()) -> None:
        self.identity = AgentIdentity(agent_id or f"{self.role}_agent:{business_id}", business_id, self.role)
        self.objective = objective
        self.permissions = tuple(permissions)
        self.status = "idle"
        self.last_task_id: str | None = None
        self.handled_messages = 0
        self.decisions = 0
        self.started_at = datetime.now(timezone.utc)

    @property
    def agent_id(self) -> str:
        return self.identity.agent_id

    @property
    def business_id(self) -> str:
        return self.identity.business_id

    def task(self, *, task_type: str, payload: dict[str, Any], correlation_id: str | None = None) -> AgentTask:
        task = AgentTask(
            task_type=task_type,
            business_id=self.business_id,
            assigned_agent_id=self.agent_id,
            correlation_id=correlation_id,
            payload=payload,
        )
        self.last_task_id = task.task_id
        return task

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "business_id": self.business_id,
            "role": self.role,
            "objective": self.objective,
            "permissions": list(self.permissions),
            "status": self.status,
            "last_task_id": self.last_task_id,
            "handled_messages": self.handled_messages,
            "decisions": self.decisions,
            "decision_mode": "deterministic_policy",
            "memory": "durable_session_scoped",
        }

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        self.handled_messages += 1

    def _proposal_payload(self, proposal: Proposal) -> dict[str, Any]:
        return proposal.model_dump(by_alias=True)
