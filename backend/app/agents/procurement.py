from __future__ import annotations

from dataclasses import dataclass

from app.events.schemas import Proposal
from .llm_gateway import LLMGateway


class ProcurementAgent:
    role = "procurement"

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway or LLMGateway()

    def propose(self, context: dict) -> Proposal:
        """Return only a validated proposal; no engine mutation happens here."""
        return self.gateway.propose(context)

