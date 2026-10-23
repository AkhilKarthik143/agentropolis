"""Controller policy checks for consequential finance actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerDecision:
    decision: str
    reason: str
    approval_required: bool = False


class ControllerService:
    role = "controller"

    def review(self, *, amount_cents: int, spend_limit_cents: int, supplier_reliability: float, reliability_floor: float = 0.35, reserve_ok: bool = True, approval_threshold_cents: int = 150_000) -> ControllerDecision:
        if not reserve_ok:
            return ControllerDecision("REJECT", "minimum reserve would be breached")
        if amount_cents > spend_limit_cents:
            return ControllerDecision("REJECT", "spend limit exceeded")
        if supplier_reliability < reliability_floor:
            return ControllerDecision("REJECT", "supplier reliability is below policy")
        if amount_cents >= approval_threshold_cents:
            return ControllerDecision("NEEDS_HUMAN", "exceptional spend requires human approval", approval_required=True)
        return ControllerDecision("APPROVE", "controller policy checks passed")
