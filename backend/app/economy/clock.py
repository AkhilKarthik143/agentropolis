from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimClock:
    day: int = 1
    tick: int = 0

    def advance(self, days: int = 0, ticks: int = 1) -> None:
        self.day += days
        self.tick += ticks

    def now(self) -> str:
        return f"sim-day-{self.day:03d}-tick-{self.tick:04d}"

