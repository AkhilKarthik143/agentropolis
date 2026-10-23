from __future__ import annotations

from typing import Any

from .base import AgentContext, BaseBusinessAgent
from app.events.schemas import AgentMessage, AgentMessageType, Proposal


class PaymentsAgent(BaseBusinessAgent):
    """Submits authorized payment proposals; it cannot call the bank directly."""

    role = "payments"

    def __init__(self, *, business_id: str) -> None:
        super().__init__(business_id=business_id, objective="pay only approved and matched obligations", permissions=("submit_approved_payment",))

    def submit(self, proposal: Proposal, context: AgentContext) -> None:
        self.status = "working"
        outcome = context.engine.submit_proposal(proposal)
        self.decisions += 1
        context.record_action(outcome.as_dict())
        context.emit(
            "AgentActionResult",
            business_id=self.business_id,
            deal_id=proposal.deal_id,
            proposal=proposal,
            payload={"agent_id": self.agent_id, "outcome": outcome.as_dict()},
            idempotency_key=f"agent-action:{proposal.idempotency_key}",
        )
        self.status = "idle"

    def handle_message(self, message: AgentMessage, context: AgentContext) -> None:
        super().handle_message(message, context)
        if message.message_type is not AgentMessageType.ACTION_PROPOSAL:
            return
        proposal = Proposal.model_validate(message.payload["proposal"])
        self.submit(proposal, context)
