"""CRS Credit adapter seam with a deterministic demo fixture."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreditResult:
    supplier_id: str
    status: str
    score: int
    reason: str
    mode: str = "mock"


class MockCRSCredit:
    mode = "mock"

    def check_supplier(self, supplier_id: str) -> CreditResult:
        if supplier_id == "supplier_shady":
            return CreditResult(supplier_id, "blocked", 18, "sandbox identity failed credit/fraud policy")
        return CreditResult(supplier_id, "passed", 82, "sandbox identity passed seeded policy checks")


class CRSCreditAdapter(MockCRSCredit):
    """Explicitly unverified live seam; no endpoint is guessed."""

    mode = "unverified"

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint

    def check_supplier(self, supplier_id: str) -> CreditResult:
        raise RuntimeError("CRS Credit live endpoint is not verified; use MockCRSCredit or the official sandbox brief")
