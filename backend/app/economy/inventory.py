from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inventory:
    quantities: dict[str, int] = field(default_factory=dict)
    reservations: dict[str, dict] = field(default_factory=dict)

    def add(self, item: str, quantity: int) -> int:
        if type(quantity) is not int or quantity < 0:
            raise ValueError("inventory additions must be non-negative")
        self.quantities[item] = self.quantities.get(item, 0) + quantity
        return self.quantities[item]

    def consume(self, item: str, quantity: int) -> int:
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("inventory consumption must be positive")
        current = self.quantities.get(item, 0)
        if self.available(item) < quantity:
            raise ValueError(f"insufficient inventory for {item}")
        self.quantities[item] = current - quantity
        return self.quantities[item]

    def quantity(self, item: str) -> int:
        return self.quantities.get(item, 0)

    def available(self, item: str) -> int:
        return self.quantity(item) - sum(
            r["quantity"] for r in self.reservations.values() if r["item"] == item
        )

    def reserve(self, reservation_id: str, item: str, quantity: int) -> None:
        if reservation_id in self.reservations:
            if self.reservations[reservation_id] != {
                "item": item,
                "quantity": quantity,
            }:
                raise ValueError("reservation identity reused with different terms")
            return
        if (
            type(quantity) is not int
            or quantity <= 0
            or self.available(item) < quantity
        ):
            raise ValueError("insufficient available stock")
        self.reservations[reservation_id] = {"item": item, "quantity": quantity}

    def release(self, reservation_id: str) -> None:
        self.reservations.pop(reservation_id, None)

    def fulfill(self, reservation_id: str, quantity: int) -> None:
        reservation = self.reservations.get(reservation_id)
        if reservation is None or quantity <= 0 or quantity > reservation["quantity"]:
            raise ValueError("invalid fulfillment quantity")
        self.quantities[reservation["item"]] -= quantity
        reservation["quantity"] -= quantity
        if reservation["quantity"] == 0:
            self.release(reservation_id)
