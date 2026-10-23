from __future__ import annotations

from .base import AgentContext, BaseBusinessAgent
from app.events.schemas import AgentMessage, AgentMessageType, AgentTaskStatus


class ManagerAgent(BaseBusinessAgent):
    """Turns operating signals into scoped tasks for a business team."""

    role = "manager"

    def __init__(self, *, business_id: str, objective: str) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("assign_tasks", "read_team_status"))

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.INVENTORY_LOW:
            return
        procurement = context.registry.by_role(self.business_id, "procurement")
        if procurement is None:
            self.status = "failed"
            return
        task = self.task(task_type="source_inventory", payload=message.payload, correlation_id=message.correlation_id)
        task.status = AgentTaskStatus.RUNNING
        context.emit(
            "AgentTaskAssigned",
            business_id=self.business_id,
            deal_id=message.correlation_id,
            payload={"task": task.model_dump(mode="json"), "manager_agent_id": self.agent_id},
            idempotency_key=f"task:{task.task_id}",
        )
        context.send(
            message_type=AgentMessageType.TASK_ASSIGNED,
            sender_id=self.agent_id,
            recipient_id=procurement.agent_id,
            business_id=self.business_id,
            correlation_id=message.correlation_id,
            payload={"task": task.model_dump(mode="json")},
            idempotency_key=f"task-message:{task.task_id}",
        )
