from __future__ import annotations

from .base import AgentContext, BaseBusinessAgent
from app.events.schemas import AgentMessage, AgentMessageType


class ManagerAgent(BaseBusinessAgent):
    """Converts needs to idempotent, business-owned procurement tasks."""
    role = "manager"

    def __init__(self, *, business_id: str, objective: str) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("assign_tasks", "read_team_status"))

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is AgentMessageType.ACTION_RESULT:
            context.remember(self.agent_id, "last_action_result", message.payload)
            return
        if message.message_type is not AgentMessageType.INVENTORY_LOW:
            return
        procurement = context.registry.by_role(self.business_id, "procurement")
        if procurement is None:
            raise RuntimeError("procurement agent unavailable")
        task = self.task(task_type="source_inventory", payload=message.payload, correlation_id=message.correlation_id)
        task.task_id = f"task:{message.idempotency_key}"
        task.assigned_agent_id = procurement.agent_id
        self.last_task_id = task.task_id
        existing = next((item for item in context.registry.store.tasks() if item["task_id"] == task.task_id), None)
        if existing is None:
            context.registry.store.save_task(task)
        self.decisions += 1
        context.emit("AgentTaskAssigned", business_id=self.business_id, deal_id=message.correlation_id, payload={"task": task.model_dump(mode="json"), "manager_agent_id": self.agent_id}, idempotency_key=f"task:{task.task_id}")
        context.send(message_type=AgentMessageType.TASK_ASSIGNED, sender_id=self.agent_id, recipient_id=procurement.agent_id, business_id=self.business_id, correlation_id=message.correlation_id, payload={"task": task.model_dump(mode="json")}, idempotency_key=f"task-message:{task.task_id}")
