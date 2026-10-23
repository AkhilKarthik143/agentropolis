from __future__ import annotations

from dataclasses import dataclass

from app.economy.engine import EconomyEngine
from app.events.schemas import Proposal

from .procurement import ProcurementAgent
from .treasury_risk import TreasuryRiskAgent


@dataclass
class OrchestratorCore:
    """Coordinator facade for the in-process MVP topology.

    This class can emit proposals and recommendations, but all state-changing
    work remains in ``EconomyEngine.submit_proposal``.
    """

    engine: EconomyEngine
    procurement: ProcurementAgent
    treasury_risk: TreasuryRiskAgent

    @classmethod
    def create(cls, engine: EconomyEngine) -> "OrchestratorCore":
        return cls(engine, ProcurementAgent(), TreasuryRiskAgent())

    def review(self, proposal: Proposal):
        return self.treasury_risk.review(self.engine, proposal)

    def execute(self, proposal: Proposal):
        """Submit a typed proposal to the deterministic command handler."""
        return self.engine.submit_proposal(proposal)
