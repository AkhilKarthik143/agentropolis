from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inventory:
    quantities: dict[str, int] = field(default_factory=dict)

    def add(self, item: str, quantity: int) -> int:
        if quantity < 0:
            raise ValueError("inventory additions must be non-negative")
        self.quantities[item] = self.quantities.get(item, 0) + quantity
        return self.quantities[item]

    def consume(self, item: str, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("inventory consumption must be positive")
        current = self.quantities.get(item, 0)
        if current < quantity:
            raise ValueError(f"insufficient inventory for {item}")
        self.quantities[item] = current - quantity
        return self.quantities[item]

    def quantity(self, item: str) -> int:
        return self.quantities.get(item, 0)

