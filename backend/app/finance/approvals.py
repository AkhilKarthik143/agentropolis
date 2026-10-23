from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"


@dataclass
class ApprovalRequest:
    approval_id: str
    proposal_id: str
    business_id: str
    amount_cents: int
    proposer: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: str | None = None
    reason: str = ""
    poster: str | None = None
    decision_state: str = "PENDING"


class ApprovalError(ValueError):
    pass


class ApprovalManager:
    def __init__(self, threshold_cents: int = 1_500_00, minimum_reserve_cents: int = 2_000_00) -> None:
        self.threshold_cents = threshold_cents
        self.minimum_reserve_cents = minimum_reserve_cents
        self.requests: dict[str, ApprovalRequest] = {}
        self._lock = Lock()
        self._counter = 0

    def requires_approval(self, amount_cents: int) -> bool:
        return amount_cents >= self.threshold_cents

    def request(self, proposal_id: str, business_id: str, amount_cents: int, proposer: str, reason: str = "", *, needs_human: bool = False) -> ApprovalRequest:
        with self._lock:
            self._counter += 1
            request = ApprovalRequest(f"approval_{self._counter:04d}", proposal_id, business_id, amount_cents, proposer, reason=reason, decision_state="NEEDS_HUMAN" if needs_human else "PENDING")
            self.requests[request.approval_id] = request
        return request

    def decide(self, approval_id: str, approver: str, granted: bool, poster: str | None = None) -> ApprovalRequest:
        with self._lock:
            request = self.requests.get(approval_id)
            if request is None:
                raise ApprovalError("approval request not found")
            if request.status is not ApprovalStatus.PENDING:
                raise ApprovalError("approval request is already resolved")
            if approver == request.proposer:
                raise ApprovalError("separation of duties: proposer cannot approve")
            if poster and poster in {request.proposer, approver}:
                raise ApprovalError("separation of duties: poster must be independent")
            request.approver = approver
            request.poster = poster
            request.status = ApprovalStatus.GRANTED if granted else ApprovalStatus.DENIED
            return request

    def pending(self, business_id: str | None = None) -> list[ApprovalRequest]:
        return [r for r in self.requests.values() if r.status is ApprovalStatus.PENDING and (business_id is None or r.business_id == business_id)]

    def snapshot(self) -> list[dict]:
        return [{"approval_id": r.approval_id, "proposal_id": r.proposal_id, "business_id": r.business_id, "amount_cents": r.amount_cents, "proposer": r.proposer, "status": r.status.value, "decision_state": r.decision_state, "approver": r.approver, "reason": r.reason} for r in self.requests.values()]

