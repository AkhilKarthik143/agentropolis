from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyAgent:
    name: str
    seed: str
    port: int | None = None
    roles: tuple[str, ...] = ("strategy", "procurement", "treasury", "accountant", "risk")
    transport: str = "inprocess"


def create_company_agent(*, name: str, seed: str, port: int | None = None, transport: str = "inprocess", **_: object) -> CompanyAgent:
    return CompanyAgent(name=name, seed=seed, port=port, transport=transport)

