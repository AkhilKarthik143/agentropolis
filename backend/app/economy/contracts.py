from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .state_machine import EconomyState, IllegalTransition, transition


class ContractStatus(StrEnum):
    OFFERED = "offered"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    INVOICED = "invoiced"
    PAID = "paid"
    DEFAULTED = "defaulted"


@dataclass
class Contract:
    contract_id: str
    buyer_id: str
    supplier_id: str
    item: str
    quantity: int
    unit_price_cents: int
    total_cents: int
    delivery_days: int
    status: ContractStatus
    proposal_id: str
    rationale: str
    reliability: float
    state: EconomyState = EconomyState.PAYMENT_RECORDED
    delivery_mode: str = "immediate"
    delivered_quantity: int = 0

    def transition(self, status: ContractStatus) -> None:
        allowed = {
            ContractStatus.OFFERED: {ContractStatus.COUNTERED, ContractStatus.ACCEPTED, ContractStatus.DEFAULTED},
            ContractStatus.COUNTERED: {ContractStatus.ACCEPTED, ContractStatus.DEFAULTED},
            ContractStatus.ACCEPTED: {ContractStatus.DELIVERED, ContractStatus.INVOICED, ContractStatus.DEFAULTED},
            ContractStatus.DELIVERED: {ContractStatus.INVOICED, ContractStatus.PAID},
            ContractStatus.INVOICED: {ContractStatus.PAID, ContractStatus.DEFAULTED},
            ContractStatus.PAID: set(),
            ContractStatus.DEFAULTED: set(),
        }
        if status not in allowed[self.status]:
            raise ValueError(f"invalid contract transition {self.status} -> {status}")
        self.status = status

    def transition_state(self, state: EconomyState | str) -> None:
        self.state = transition(self.state, state)

    @property
    def session_state(self) -> str:
        return self.state.value

