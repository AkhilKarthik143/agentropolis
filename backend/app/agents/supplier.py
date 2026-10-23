from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupplierProfile:
    supplier_id: str
    inventory: int
    unit_price_cents: int
    delivery_days: int
    reliability: float
    bankrupt: bool = False
    negotiation_style: str = "steady"


class SupplierAgent:
    role = "supplier"

    def __init__(self, profile: SupplierProfile | None = None) -> None:
        self.profile = profile

    @property
    def available(self) -> bool:
        return bool(self.profile and not self.profile.bankrupt and self.profile.inventory > 0)

