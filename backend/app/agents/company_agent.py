from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re


@dataclass
class CompanyAgent:
    """Persistent identity and team lifecycle for one simulated business."""

    name: str
    seed: str
    business_id: str | None = None
    port: int | None = None
    objective: str = "maintain reserve and source reliable suppliers"
    roles: tuple[str, ...] = ("manager", "inventory", "procurement", "negotiation", "treasury", "risk", "payments")
    transport: str = "inprocess"
    status: str = "created"
    task_ids: list[str] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.business_id:
            slug = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_")
            self.business_id = slug or "business"
        if self.task_ids is None:
            self.task_ids = []

    def start(self) -> None:
        self.status = "running"

    def stop(self) -> None:
        self.status = "stopped"

    def assign_task(self, task_id: str) -> None:
        self.task_ids = [*(self.task_ids or []), task_id]

    def status_snapshot(self) -> dict[str, object]:
        return {
            "business_id": self.business_id,
            "name": self.name,
            "objective": self.objective,
            "roles": list(self.roles),
            "transport": self.transport,
            "status": self.status,
            "task_count": len(self.task_ids or []),
        }


def create_company_agent(*, name: str, seed: str, port: int | None = None, transport: str = "inprocess", **_: object) -> CompanyAgent:
    return CompanyAgent(name=name, seed=seed, port=port, transport=transport)

