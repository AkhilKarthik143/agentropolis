from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PricingSignal:
    supplier_id: str
    unit_price_cents: int
    reliability: float
    delivery_days: int

    @property
    def score(self) -> float:
        return self.reliability * 100 - self.unit_price_cents / 100 - self.delivery_days


def choose_supplier(signals: list[PricingSignal], minimum_reliability: float = 0.5) -> PricingSignal | None:
    eligible = [signal for signal in signals if signal.reliability >= minimum_reliability and signal.unit_price_cents > 0]
    return max(eligible, key=lambda signal: signal.score, default=None)

