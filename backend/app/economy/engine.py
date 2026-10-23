from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from app.events.audit import verify_chain
from app.events.bus import EventBus
from app.events.schemas import EventEnvelope, Proposal, ProposalType, ValidationResult
from app.finance.approvals import ApprovalManager, ApprovalStatus
from app.finance.banking import BankError, MockBank
from app.finance.controls import FinanceControlError, FinanceControls, GoodsReceipt, PurchaseOrder, SupplierInvoice, default_roles
from app.finance.ledger import Account, JournalEntry, Ledger, LedgerLine
from app.integrations.crs_credit import MockCRSCredit
from app.integrations.coinbase_x402 import MockX402, X402Rail
from app.security.gate import inspect_proposal

from app.agents.llm_gateway import LLMGateway

from .clock import SimClock
from .contracts import Contract, ContractStatus
from .inventory import Inventory
from .scoring import score_offer
from .state_machine import EconomyState


@dataclass
class Business:
    business_id: str
    name: str
    kind: str
    role: str
    reliability: float
    reserve_cents: int
    spend_limit_cents: int
    categories: list[str] = field(default_factory=list)
    inventory: Inventory = field(default_factory=Inventory)
    account_id: str = ""
    active: bool = True
    bank: str = "MockBank"
    objective: str = "maintain reserve and source reliable suppliers"
    inventory_item: str = "coffee_beans"
    low_stock_threshold: int = 8
    negotiation_style: str = "steady"
    credit_status: str = "passed"
    credit_score: int = 82
    credit_reason: str = "seeded demo credit result"
    supplier_note: str = ""
    capacity: dict[str, int] = field(default_factory=dict)


@dataclass
class ProposalOutcome:
    status: str
    proposal_id: str
    deal_id: str | None = None
    approval_id: str | None = None
    reason: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "proposal_id": self.proposal_id, "deal_id": self.deal_id, "approval_id": self.approval_id, "reason": self.reason, "validation": self.validation}


class EconomyEngine:
    """Serialized command handler: agents propose, this object mutates state."""

    def __init__(self, bus: EventBus | None = None, ledger: Ledger | None = None, approvals: ApprovalManager | None = None, bank: MockBank | None = None, seed: int = 13, session_id: str = "demo_001", controls: FinanceControls | None = None, llm: LLMGateway | None = None) -> None:
        self.bus = bus or EventBus()
        self.ledger = ledger or Ledger()
        self.approvals = approvals or ApprovalManager()
        self.bank = bank or MockBank()
        self.controls = controls or FinanceControls()
        self.llm = llm or LLMGateway(mode="replay")
        self.credit = MockCRSCredit()
        self.x402 = X402Rail(MockX402())
        self.clock = SimClock()
        self.rng = random.Random(seed)
        self.session_id = session_id
        self.businesses: dict[str, Business] = {}
        self.contracts: dict[str, Contract] = {}
        self.offers: dict[str, dict[str, Any]] = {}
        self._outcomes: dict[str, ProposalOutcome] = {}
        self._pending: dict[str, Proposal] = {}
        self._lock = RLock()
        self._event_epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.agent_runtime: Any | None = None

    def attach_agent_runtime(self, runtime: Any) -> None:
        """Attach the event-driven team scheduler after businesses are seeded."""
        self.agent_runtime = runtime

    def _event_time(self) -> datetime:
        return self._event_epoch + timedelta(seconds=len(self.bus.replay()))

    def _emit(self, event_type: str, business_id: str | None = None, deal_id: str | None = None, proposal: Proposal | None = None, payload: dict[str, Any] | None = None, idempotency_key: str | None = None) -> EventEnvelope:
        data = dict(payload or {})
        if proposal:
            data.setdefault("proposal", proposal.model_dump(by_alias=True))
            data.setdefault("public_rationale", proposal.public_rationale or proposal.rationale)
            data.setdefault("private_rationale", proposal.private_rationale)
        return self.bus.append(EventEnvelope(ts=self._event_time(), type=event_type, session_id=self.session_id, business_id=business_id, deal_id=deal_id, correlation_id=deal_id or (proposal.deal_id if proposal else None), idempotency_key=idempotency_key, payload=data))

    def _transition_contract(self, contract: Contract, target: EconomyState, *, proposal: Proposal | None = None, payload: dict[str, Any] | None = None) -> None:
        previous = contract.state
        contract.transition_state(target)
        self._emit(
            "StateTransition",
            contract.buyer_id,
            contract.contract_id,
            proposal=proposal,
            payload={"from_state": previous.value, "to_state": contract.state.value, **(payload or {})},
            idempotency_key=f"state:{contract.contract_id}:{contract.state.value}",
        )

    def register_business(self, business: Business, opening_cents: int | None = None) -> Business:
        with self._lock:
            if business.business_id in self.businesses:
                return self.businesses[business.business_id]
            opening = opening_cents if opening_cents is not None else max(business.reserve_cents, 0)
            business.account_id = self.bank.create_account(business.business_id, opening)
            self.ledger.seed_cash(business.business_id, opening)
            self.businesses[business.business_id] = business
            self._emit("BusinessRegistered", business.business_id, payload={"business": self.business_snapshot(business.business_id), "bank_mode": self.bank.mode}, idempotency_key=f"business:{business.business_id}")
            return business

    def business_snapshot(self, business_id: str) -> dict[str, Any]:
        business = self.businesses[business_id]
        cash = self.ledger.balance(business_id, Account.CASH)
        return {"business_id": business.business_id, "name": business.name, "kind": business.kind, "role": business.role, "reliability": business.reliability, "reserve_cents": business.reserve_cents, "spend_limit_cents": business.spend_limit_cents, "objective": business.objective, "categories": list(business.categories), "inventory": dict(business.inventory.quantities), "inventory_item": business.inventory_item, "low_stock_threshold": business.low_stock_threshold, "negotiation_style": business.negotiation_style, "credit_status": business.credit_status, "credit_score": business.credit_score, "credit_reason": business.credit_reason, "supplier_note": business.supplier_note, "capacity": dict(business.capacity), "cash_cents": cash, "account_id": business.account_id, "active": business.active, "bank": business.bank}

    def _validate(self, proposal: Proposal) -> tuple[ValidationResult, int]:
        if proposal.business_id not in self.businesses:
            return ValidationResult(ok=False, stage="authorization", reason_code="UNKNOWN_BUSINESS", message="proposing business is not registered"), 0
        buyer = self.businesses[proposal.business_id]
        if proposal.proposal_type not in {ProposalType.OFFER, ProposalType.COUNTER_OFFER}:
            return ValidationResult(ok=False, stage="schema", reason_code="UNSUPPORTED_PROPOSAL", message="this command path accepts offers and counter-offers"), 0
        if not proposal.counterparty_id or proposal.counterparty_id not in self.businesses:
            return ValidationResult(ok=False, stage="counterparty", reason_code="UNKNOWN_COUNTERPARTY", message="counterparty is not registered"), 0
        supplier = self.businesses[proposal.counterparty_id]
        if proposal.counterparty_id == proposal.business_id or not supplier.active:
            return ValidationResult(ok=False, stage="counterparty", reason_code="COUNTERPARTY_UNAVAILABLE", message="counterparty is unavailable"), 0
        if proposal.deal_id and proposal.deal_id in self.contracts:
            return ValidationResult(ok=False, stage="authorization", reason_code="STALE_OFFER", message="deal already has an executed contract"), 0
        if proposal.quantity is None or proposal.unit_price_cents is None or not proposal.item:
            return ValidationResult(ok=False, stage="schema", reason_code="INCOMPLETE_OFFER", message="offer requires item, quantity, and unit price"), 0
        amount = proposal.total_cents if proposal.total_cents is not None else proposal.quantity * proposal.unit_price_cents
        if amount <= 0:
            return ValidationResult(ok=False, stage="schema", reason_code="NON_POSITIVE_TOTAL", message="offer total must be positive"), 0
        cash = self.ledger.balance(buyer.business_id, Account.CASH)
        if cash - amount < buyer.reserve_cents:
            return ValidationResult(ok=False, stage="cash_and_reserve", reason_code="RESERVE_VIOLATION", message="offer would breach the minimum reserve", details={"cash_cents": cash, "amount_cents": amount, "reserve_cents": buyer.reserve_cents}), amount
        if amount > buyer.spend_limit_cents:
            return ValidationResult(ok=False, stage="spend_limit", reason_code="SPEND_LIMIT", message="offer exceeds the business spend limit", details={"spend_limit_cents": buyer.spend_limit_cents}), amount
        if supplier.reliability < 0.35:
            return ValidationResult(ok=False, stage="counterparty", reason_code="LOW_RELIABILITY", message="counterparty reliability is below policy", details={"reliability": supplier.reliability}), amount
        return ValidationResult(ok=True, stage="validated", message="proposal passed deterministic policy checks", details={"amount_cents": amount}), amount

    def _ensure_finance_records(self, proposal: Proposal, amount: int):
        """Create deterministic PO/AP records before the engine can pay."""

        metadata = proposal.metadata or {}
        po_id = f"po_{proposal.idempotency_key}"
        invoice_id = f"invoice_{proposal.idempotency_key}"
        receipt_id = f"receipt_{proposal.idempotency_key}"
        roles_data = metadata.get("roles") or {}
        roles = default_roles(proposal.agent_id)
        if roles_data:
            from app.finance.controls import RoleAssignment
            roles = RoleAssignment(
                requester=str(roles_data.get("requester", proposal.agent_id)),
                approver=str(roles_data.get("approver", "treasury_risk_agent")),
                payer=str(roles_data.get("payer", "payment_service")),
                poster=str(roles_data.get("poster", "accounting_service")),
            )
        self.controls.create_po(PurchaseOrder(
            po_id=po_id,
            business_id=proposal.business_id,
            supplier_id=str(proposal.counterparty_id),
            item=str(proposal.item),
            quantity=int(proposal.quantity or 0),
            unit_price_cents=int(proposal.unit_price_cents or 0),
            total_cents=amount,
            payment_terms=str(proposal.payment_terms or "on delivery"),
            cost_center=str(metadata.get("cost_center", "COFFEE-OPS")),
            roles=roles,
        ))
        self.controls.record_receipt(GoodsReceipt(receipt_id, po_id, int(metadata.get("received_quantity", proposal.quantity or 0)), "2026-01-01"))
        invoice_amount = int(metadata.get("invoice_total_cents", amount))
        self.controls.record_invoice(SupplierInvoice(
            invoice_id=invoice_id,
            invoice_number=str(metadata.get("invoice_number", f"INV-{proposal.proposal_id}")),
            po_id=po_id,
            supplier_id=str(proposal.counterparty_id),
            amount_cents=invoice_amount,
            due_date=str(metadata.get("due_date", "2026-01-08")),
            payment_terms=str(proposal.payment_terms or "on delivery"),
            tax_cents=int(metadata.get("tax_cents", 0)),
            cost_center=str(metadata.get("cost_center", "COFFEE-OPS")),
        ))
        return self.controls.match(f"match_{proposal.idempotency_key}", po_id, invoice_id, receipt_id)

    def submit_proposal(self, proposal: Proposal) -> ProposalOutcome:
        with self._lock:
            if proposal.idempotency_key in self._outcomes:
                return self._outcomes[proposal.idempotency_key]
            gate = inspect_proposal(proposal)
            if not gate.allowed:
                self._emit("ACTION_BLOCKED", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"reason": gate.reason, "code": gate.code}, idempotency_key=f"blocked:{proposal.idempotency_key}")
                outcome = ProposalOutcome("blocked", proposal.proposal_id, reason=gate.reason, validation={"reason_code": gate.code})
                self._outcomes[proposal.idempotency_key] = outcome
                return outcome
            validation, amount = self._validate(proposal)
            decision_payload = {"validation": validation.model_dump(), "executed_outcome": {}}
            if not validation.ok:
                self._emit("StateTransition", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "TREASURY_CHECK", "to_state": "REJECTED", "reason": validation.reason_code}, idempotency_key=f"state-rejected:{proposal.idempotency_key}")
                self._emit("ProposalRejected", proposal.business_id, proposal.deal_id, proposal=proposal, payload={**decision_payload, "reason_code": validation.reason_code}, idempotency_key=f"decision:{proposal.idempotency_key}")
                outcome = ProposalOutcome("rejected", proposal.proposal_id, reason=validation.message, validation=validation.model_dump())
                self._outcomes[proposal.idempotency_key] = outcome
                return outcome
            try:
                match = self._ensure_finance_records(proposal, amount)
            except FinanceControlError as exc:
                self._emit("ACTION_BLOCKED", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"reason": str(exc), "code": "FINANCE_CONTROL"}, idempotency_key=f"finance-blocked:{proposal.idempotency_key}")
                outcome = ProposalOutcome("blocked", proposal.proposal_id, reason=str(exc), validation={"reason_code": "FINANCE_CONTROL"})
                self._outcomes[proposal.idempotency_key] = outcome
                return outcome
            needs_human = match.status.value != "matched"
            if needs_human or self.approvals.requires_approval(amount):
                reason = "invoice mismatch requires human resolution" if needs_human else f"${amount / 100:,.2f} offer exceeds autonomous threshold"
                approval = self.approvals.request(proposal.proposal_id, proposal.business_id, amount, proposal.agent_id, reason=reason, needs_human=True)
                if needs_human:
                    self._emit("InvoiceMismatch", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"match": self.controls.snapshot()["matches"][-1]}, idempotency_key=f"invoice-mismatch:{proposal.idempotency_key}")
                    self._emit("RECORD_CONFLICT", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"reason": reason}, idempotency_key=f"record-conflict:{proposal.idempotency_key}")
                    self._emit("ACTION_BLOCKED", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"reason": reason, "code": "RECORD_CONFLICT"}, idempotency_key=f"record-blocked:{proposal.idempotency_key}")
                self._pending[approval.approval_id] = proposal
                self._emit("ApprovalRequested", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"approval_id": approval.approval_id, **decision_payload}, idempotency_key=f"approval:{proposal.idempotency_key}")
                outcome = ProposalOutcome("approval_required", proposal.proposal_id, approval_id=approval.approval_id, validation=validation.model_dump())
                self._outcomes[proposal.idempotency_key] = outcome
                return outcome
            self._emit("StateTransition", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "TREASURY_CHECK", "to_state": "APPROVED", "reason": "deterministic policy approved"}, idempotency_key=f"state-approved:{proposal.idempotency_key}")
            self._emit("StateTransition", proposal.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "APPROVED", "to_state": "CONTRACTED"}, idempotency_key=f"state-contracted:{proposal.idempotency_key}")
            outcome = self._execute(proposal, validation, amount)
            self._outcomes[proposal.idempotency_key] = outcome
            return outcome

    def _execute(self, proposal: Proposal, validation: ValidationResult, amount: int) -> ProposalOutcome:
        buyer = self.businesses[proposal.business_id]
        supplier = self.businesses[proposal.counterparty_id or ""]
        deal_id = proposal.deal_id or f"deal_{len(self.contracts) + 1:04d}"
        risk_explanation = self.llm.explain_risk({"validation": validation.model_dump(), "amount_cents": amount, "supplier_id": supplier.business_id})
        self._emit("RiskChecked", buyer.business_id, deal_id, proposal=proposal, payload={"validation": validation.model_dump(), "risk": "within_policy", "claude": risk_explanation.model_dump()})
        self._emit("TreasuryChecked", buyer.business_id, deal_id, proposal=proposal, payload={"validation": validation.model_dump(), "cash_cents": self.ledger.balance(buyer.business_id, Account.CASH)})
        bank_key = f"payment:{proposal.idempotency_key}"
        try:
            tx = self.bank.transfer(buyer.account_id, supplier.account_id, amount, proposal.item or "procurement", bank_key)
        except BankError as exc:
            self._emit("ProposalRejected", buyer.business_id, deal_id, proposal=proposal, payload={"validation": {"ok": False, "stage": "bank", "reason_code": "BANK_FAILURE", "message": str(exc)}}, idempotency_key=f"bank-failure:{proposal.idempotency_key}")
            return ProposalOutcome("rejected", proposal.proposal_id, deal_id=deal_id, reason=str(exc), validation={"stage": "bank", "reason_code": "BANK_FAILURE"})
        entry = JournalEntry(
            entry_id=f"journal_{deal_id}", business_id=buyer.business_id,
            lines=(
                LedgerLine(Account.INVENTORY, amount, buyer.business_id, proposal.item or "inventory"),
                LedgerLine(Account.ACCOUNTS_PAYABLE, -amount, buyer.business_id, "Goods receipt / AP"),
                LedgerLine(Account.ACCOUNTS_PAYABLE, amount, buyer.business_id, "Payment authorization"),
                LedgerLine(Account.CASH, -amount, buyer.business_id, "Payment"),
                LedgerLine(Account.CASH, amount, supplier.business_id, "Receipt"),
                LedgerLine(Account.REVENUE, -amount, supplier.business_id, "Sale"),
            ),
            memo=f"Procurement {proposal.item or 'item'} / PO receipt and AP payment", idempotency_key=f"ledger:{proposal.idempotency_key}",
        )
        try:
            self.ledger.post(entry)
        except Exception as exc:
            self.bank.transfer(supplier.account_id, buyer.account_id, amount, "Compensating reversal", f"reversal:{proposal.idempotency_key}")
            return ProposalOutcome("rejected", proposal.proposal_id, deal_id=deal_id, reason=f"ledger rejected transaction: {exc}", validation={"stage": "ledger", "reason_code": "LEDGER_REJECTED"})
        delivery_mode = str(proposal.metadata.get("delivery_mode", "immediate"))
        is_recovery = bool(proposal.metadata.get("recovery"))
        initial_state = EconomyState.RECOVERY_NEGOTIATION if is_recovery else EconomyState.CONTRACTED
        contract = Contract(deal_id, buyer.business_id, supplier.business_id, proposal.item or "goods", proposal.quantity or 0, proposal.unit_price_cents or 0, amount, proposal.delivery_days or 0, ContractStatus.PAID, proposal.proposal_id, proposal.public_rationale or proposal.rationale, supplier.reliability, initial_state, delivery_mode=delivery_mode)
        self.contracts[deal_id] = contract
        self._emit("ContractAccepted", buyer.business_id, deal_id, proposal=proposal, payload={"contract": self.contract_snapshot(deal_id)})
        if is_recovery:
            self._transition_contract(contract, EconomyState.REPLACEMENT_CONTRACT, proposal=proposal, payload={"recovery": True})
        self._emit("PaymentAuthorized", buyer.business_id, deal_id, proposal=proposal, payload={"amount_cents": amount})
        self._emit("PaymentRecorded", buyer.business_id, deal_id, proposal=proposal, payload={"transaction_id": tx.transaction_id, "amount_cents": amount, "rail": self.bank.mode})
        self._transition_contract(contract, EconomyState.PAYMENT_RECORDED, proposal=proposal)
        self._emit("LedgerPosted", buyer.business_id, deal_id, proposal=proposal, payload={"entry_id": entry.entry_id, "balanced": self.ledger.is_balanced()})
        self._transition_contract(contract, EconomyState.AWAITING_DELIVERY, proposal=proposal)
        if delivery_mode == "on_receipt":
            self._emit("GoodsAwaitingDelivery", buyer.business_id, deal_id, proposal=proposal, payload={"item": contract.item, "quantity": contract.quantity, "delivery_days": contract.delivery_days})
        else:
            buyer.inventory.add(contract.item, contract.quantity)
            contract.delivered_quantity = contract.quantity
            self._emit("InventoryReceiptConfirmed", buyer.business_id, deal_id, proposal=proposal, payload={"item": contract.item, "quantity": contract.quantity, "mode": "immediate_compatibility"})
        self._emit("Reconciled", buyer.business_id, deal_id, proposal=proposal, payload={"status": "pending_next_check"})
        return ProposalOutcome("executed", proposal.proposal_id, deal_id=deal_id, validation=validation.model_dump())

    def deliver_contract(self, deal_id: str) -> dict[str, Any]:
        """Confirm physical receipt after payment and contract authorization."""
        with self._lock:
            contract = self.contracts.get(deal_id)
            if contract is None:
                raise ValueError("contract not found")
            if contract.delivered_quantity >= contract.quantity:
                return self.contract_snapshot(deal_id)
            if contract.state is not EconomyState.AWAITING_DELIVERY:
                raise ValueError(f"contract is not awaiting delivery: {contract.state}")
            buyer = self.businesses[contract.buyer_id]
            buyer.inventory.add(contract.item, contract.quantity)
            contract.delivered_quantity = contract.quantity
            contract.status = ContractStatus.DELIVERED
            self._transition_contract(contract, EconomyState.DELIVERED, payload={"item": contract.item, "quantity": contract.quantity})
            self._emit("GoodsDelivered", contract.buyer_id, deal_id, payload={"supplier_id": contract.supplier_id, "item": contract.item, "quantity": contract.quantity})
            self._emit("InventoryReceiptConfirmed", contract.buyer_id, deal_id, payload={"item": contract.item, "quantity": contract.quantity, "mode": "delivery_confirmation"})
            return self.contract_snapshot(deal_id)

    def resolve_approval(self, approval_id: str, approver: str, granted: bool) -> ProposalOutcome:
        with self._lock:
            request = self.approvals.decide(approval_id, approver, granted, poster="accountant_agent")
            proposal = self._pending.pop(approval_id)
            if not granted:
                self._emit("StateTransition", request.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "TREASURY_CHECK", "to_state": "REJECTED", "reason": "human approval denied"}, idempotency_key=f"state-human-rejected:{proposal.idempotency_key}")
                self._emit("ApprovalDenied", request.business_id, proposal.deal_id, proposal=proposal, payload={"approval_id": approval_id, "approver": approver})
                outcome = ProposalOutcome("denied", proposal.proposal_id, approval_id=approval_id, reason="human approval denied")
                self._outcomes[proposal.idempotency_key] = outcome
                return outcome
            validation, amount = self._validate(proposal)
            self._emit("ApprovalGranted", request.business_id, proposal.deal_id, proposal=proposal, payload={"approval_id": approval_id, "approver": approver})
            if not validation.ok:
                outcome = ProposalOutcome("rejected", proposal.proposal_id, approval_id=approval_id, reason=validation.message, validation=validation.model_dump())
            else:
                if "invoice mismatch" in request.reason:
                    # Approval is the explicit exception path.  It creates a
                    # corrected immutable invoice record; the original stays
                    # in the audit trail as evidence of the conflict.
                    po_id = f"po_{proposal.idempotency_key}"
                    corrected_id = f"invoice_{proposal.idempotency_key}:human-approved"
                    self.controls.record_invoice(SupplierInvoice(
                        corrected_id, f"INV-{proposal.proposal_id}-CORRECTED", po_id,
                        str(proposal.counterparty_id), amount, "2026-01-08",
                        str(proposal.payment_terms or "on delivery"), 0, "COFFEE-OPS",
                    ))
                    self.controls.match(f"match_{proposal.idempotency_key}:human-approved", po_id, corrected_id, f"receipt_{proposal.idempotency_key}")
                    self._emit("RECORD_CONFLICT_RESOLVED", request.business_id, proposal.deal_id, proposal=proposal, payload={"approval_id": approval_id, "approver": approver}, idempotency_key=f"record-resolved:{proposal.idempotency_key}")
                self._emit("StateTransition", request.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "TREASURY_CHECK", "to_state": "APPROVED", "reason": "human approval granted"}, idempotency_key=f"state-human-approved:{proposal.idempotency_key}")
                self._emit("StateTransition", request.business_id, proposal.deal_id, proposal=proposal, payload={"from_state": "APPROVED", "to_state": "CONTRACTED"}, idempotency_key=f"state-human-contracted:{proposal.idempotency_key}")
                outcome = self._execute(proposal, validation, amount)
            self._outcomes[proposal.idempotency_key] = outcome
            return outcome

    def contract_snapshot(self, contract_id: str) -> dict[str, Any]:
        contract = self.contracts[contract_id]
        return {"contract_id": contract.contract_id, "buyer_id": contract.buyer_id, "supplier_id": contract.supplier_id, "item": contract.item, "quantity": contract.quantity, "delivered_quantity": contract.delivered_quantity, "delivery_mode": contract.delivery_mode, "unit_price_cents": contract.unit_price_cents, "total_cents": contract.total_cents, "delivery_days": contract.delivery_days, "status": contract.status.value, "state": contract.session_state, "proposal_id": contract.proposal_id, "rationale": contract.rationale, "reliability": contract.reliability}

    def shock(self, shock_type: str, supplier_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            user = next((b for b in self.businesses.values() if b.role == "buyer"), None)
            if user is None:
                return {"ok": False, "reason": "no buyer business"}
            normalized_shock = shock_type.lower()
            self._emit("ShockInjected", user.business_id, payload={"shock_type": normalized_shock, "supplier_id": supplier_id, "clock": self.clock.now()})
            if normalized_shock in {"supplier_bankruptcy", "supplier_bankrupt"}:
                active_contract = next((c for c in self.contracts.values() if c.buyer_id == user.business_id and c.status is not ContractStatus.DEFAULTED and (supplier_id is None or c.supplier_id == supplier_id)), None)
                if active_contract is None and supplier_id:
                    active_contract = next((c for c in self.contracts.values() if c.buyer_id == user.business_id and c.status is not ContractStatus.DEFAULTED), None)
                if active_contract:
                    supplier = self.businesses[active_contract.supplier_id]
                    supplier.active = False
                    active_contract.status = ContractStatus.DEFAULTED
                    if active_contract.state is EconomyState.AWAITING_DELIVERY:
                        self._transition_contract(active_contract, EconomyState.SUPPLIER_BANKRUPT, payload={"supplier_id": supplier.business_id, "reason": "supplier bankruptcy"})
                    self._emit("SupplierDefaulted", user.business_id, active_contract.contract_id, payload={"supplier_id": supplier.business_id, "reason": "supplier bankruptcy"})
                    self._emit("SUPPLIER_BANKRUPT", user.business_id, active_contract.contract_id, payload={"supplier_id": supplier.business_id})
                    self._emit("DELIVERY_AT_RISK", user.business_id, active_contract.contract_id, payload={"supplier_id": supplier.business_id, "item": active_contract.item})
                    self._emit("RECOVERY_STARTED", user.business_id, active_contract.contract_id, payload={"failed_supplier": supplier.business_id})
                    writeoff = JournalEntry(
                        entry_id=f"writeoff_{active_contract.contract_id}",
                        business_id=user.business_id,
                        lines=(
                            LedgerLine(Account.WRITE_OFF, active_contract.total_cents, user.business_id, "Supplier bankruptcy loss"),
                            LedgerLine(Account.INVENTORY, -active_contract.total_cents, user.business_id, "Unreceived goods write-off"),
                        ),
                        memo="Supplier bankruptcy / fraud-loss reserve",
                        idempotency_key=f"writeoff:{active_contract.contract_id}",
                    )
                    self.ledger.post(writeoff)
                    self._emit("WriteOffPosted", user.business_id, active_contract.contract_id, payload={"entry_id": writeoff.entry_id, "amount_cents": active_contract.total_cents, "balanced": self.ledger.is_balanced()})
                    if active_contract.state is EconomyState.SUPPLIER_BANKRUPT:
                        self._transition_contract(active_contract, EconomyState.RECOVERY_NEGOTIATION, payload={"failed_supplier": supplier.business_id})
                    self._emit("ReplanStarted", user.business_id, active_contract.contract_id, payload={"trigger": shock_type, "agent": "broker_agent", "failed_supplier": supplier.business_id})
                    replacement = next((b for b in self.businesses.values() if b.role == "supplier" and b.active and b.business_id != supplier.business_id and b.reliability >= 0.7), None)
                    if replacement:
                        recovery_plan = self.llm.plan_recovery({"failed_supplier": supplier.business_id, "replacement_candidates": [replacement.business_id], "item": active_contract.item})
                        self._emit("RecoveryPlanProposed", user.business_id, active_contract.contract_id, payload={"claude": recovery_plan.model_dump()})
                        recovery_number = len(self.contracts) + 1
                        proposal = Proposal(type=ProposalType.OFFER, proposal_id=f"replan_{recovery_number:04d}", idempotency_key=f"replan:{active_contract.contract_id}:{replacement.business_id}", agent_id="procurement_agent", business_id=user.business_id, counterparty_id=replacement.business_id, deal_id=f"recovery_{recovery_number:04d}", item=active_contract.item, quantity=active_contract.quantity, unit_price_cents=active_contract.unit_price_cents + 12, delivery_days=active_contract.delivery_days + 1, total_cents=(active_contract.unit_price_cents + 12) * active_contract.quantity, public_rationale="Re-sourced after a supplier bankruptcy; reliability weighted above price.", private_rationale="Recovery policy selected the highest reliability available supplier.", metadata={"recovery": True})
                        outcome = self.submit_proposal(proposal)
                        if outcome.status == "executed":
                            self._emit("REPLACEMENT_OFFER_RECEIVED", user.business_id, proposal.deal_id, proposal=proposal, payload={"supplier_id": replacement.business_id})
                            self._emit("REPLACEMENT_APPROVED", user.business_id, proposal.deal_id, proposal=proposal, payload={"supplier_id": replacement.business_id})
                            self._emit("INVENTORY_RECOVERED", user.business_id, proposal.deal_id, proposal=proposal, payload={"item": active_contract.item, "quantity": active_contract.quantity})
                            replacement_contract = self.contracts.get(proposal.deal_id or "")
                            if replacement_contract and replacement_contract.state is EconomyState.AWAITING_DELIVERY:
                                self._transition_contract(replacement_contract, EconomyState.RECOVERED, payload={"replacement_supplier": replacement.business_id})
                        return {"ok": True, "shock_type": shock_type, "replacement_supplier": replacement.business_id, "outcome": outcome.as_dict()}
            elif shock_type == "demand_spike":
                user.inventory.add("coffee_beans", 8)
                self._emit("ReplanStarted", user.business_id, payload={"trigger": shock_type, "additional_demand_units": 8})
            elif shock_type == "liquidity_crisis":
                user.reserve_cents = max(user.reserve_cents, self.approvals.minimum_reserve_cents * 2)
                self._emit("ReplanStarted", user.business_id, payload={"trigger": shock_type, "new_reserve_cents": user.reserve_cents})
            else:
                self._emit("ReplanStarted", user.business_id, payload={"trigger": shock_type, "action": "risk_agent_review"})
            return {"ok": True, "shock_type": shock_type}

    def summary(self) -> dict[str, Any]:
        payload = {"mode": "MOCK", "clock": self.clock.now(), "businesses": [self.business_snapshot(bid) for bid in self.businesses], "offers": list(self.offers.values()), "contracts": [self.contract_snapshot(cid) for cid in self.contracts], "approvals": self.approvals.snapshot(), "ledger": self.ledger.snapshot(), "trial_balance": self.ledger.trial_balance(), "ledger_proof": self.ledger.proof(), "finance": self.controls.snapshot(), "audit": verify_chain(self.bus.replay()), "events": [event.model_dump(mode="json") for event in self.bus.replay(max(0, len(self.bus.replay()) - 30))]}
        if self.agent_runtime is not None:
            payload["agent_runtime"] = self.agent_runtime.snapshot()
        return payload

    def audit_verification(self) -> dict[str, Any]:
        return verify_chain(self.bus.replay())

    def ledger_proof(self, business_id: str | None = None) -> dict[str, Any]:
        return self.ledger.proof(business_id)

    def _buy_supplier_intelligence(self, buyer: Business, supplier: Business, tick_key: str) -> dict[str, Any]:
        """Pay the seeded reliability-report agent through the x402 mock rail."""

        fee_cents = 100
        try:
            receipt = self.x402.pay(fee_cents, f"supplier-report:{supplier.business_id}:{tick_key}")
        except (RuntimeError, ValueError) as exc:
            self._emit("X402_PAYMENT_BLOCKED", buyer.business_id, payload={"supplier_id": supplier.business_id, "reason": str(exc), "mode": self.x402.mode}, idempotency_key=f"x402-blocked:{supplier.business_id}:{tick_key}")
            return {"status": "unavailable", "reason": str(exc), "mode": self.x402.mode}
        entry = JournalEntry(
            entry_id=f"x402_fee_{supplier.business_id}_{tick_key}",
            business_id=buyer.business_id,
            lines=(LedgerLine(Account.FEES, fee_cents, buyer.business_id, "Supplier reliability report"), LedgerLine(Account.CASH, -fee_cents, buyer.business_id, "x402 supplier-intelligence payment")),
            memo="x402 supplier-intelligence report",
            idempotency_key=f"x402-ledger:{supplier.business_id}:{tick_key}",
        )
        self.ledger.post(entry)
        report = {"status": "received", "supplier_id": supplier.business_id, "reliability": supplier.reliability, "receipt_id": receipt.receipt_id, "tx_hash": receipt.tx_hash, "mode": receipt.mode, "ledger_entry_id": entry.entry_id}
        self._emit("X402_SUPPLIER_INTELLIGENCE_PAID", buyer.business_id, payload=report, idempotency_key=f"x402:{supplier.business_id}:{tick_key}")
        return report

    def _legacy_tick(self) -> list[dict[str, Any]]:
        """Run one autonomous scheduler tick; user prompts are not required."""
        with self._lock:
            self.clock.advance(ticks=1)
            actions: list[dict[str, Any]] = []
            for buyer in self.businesses.values():
                if buyer.role != "buyer":
                    continue
                current = buyer.inventory.quantity(buyer.inventory_item)
                if current > buyer.low_stock_threshold:
                    continue
                suppliers = [candidate for candidate in self.businesses.values() if candidate.role == "supplier" and candidate.active and buyer.inventory_item in candidate.categories]
                self._emit("NeedDetected", buyer.business_id, payload={"item": buyer.inventory_item, "quantity_on_hand": current, "threshold": buyer.low_stock_threshold, "trigger": "sim_clock"}, idempotency_key=f"need:{buyer.business_id}:{self.clock.day}:{self.clock.tick}")
                eligible_suppliers: list[tuple[Business, dict[str, Any]]] = []
                for candidate in suppliers:
                    if candidate.supplier_note:
                        gate = inspect_proposal(Proposal(type=ProposalType.OFFER, agent_id=f"supplier_agent:{candidate.business_id}", business_id=buyer.business_id, counterparty_id=candidate.business_id, item=buyer.inventory_item, quantity=1, unit_price_cents=1, total_cents=1, metadata={"supplier_note": candidate.supplier_note}))
                        if not gate.allowed:
                            self._emit("ACTION_BLOCKED", buyer.business_id, payload={"supplier_id": candidate.business_id, "reason": gate.reason, "code": gate.code}, idempotency_key=f"supplier-note-blocked:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                    credit = self.credit.check_supplier(candidate.business_id)
                    candidate.credit_status, candidate.credit_score, candidate.credit_reason = credit.status, credit.score, credit.reason
                    self._emit("CRS_CHECKED", buyer.business_id, payload={"supplier_id": candidate.business_id, "status": credit.status, "score": credit.score, "reason": credit.reason, "mode": credit.mode}, idempotency_key=f"crs:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                    if credit.status == "blocked":
                        self._emit("SUPPLIER_BLOCKED", buyer.business_id, payload={"supplier_id": candidate.business_id, "reason": credit.reason, "ledger_free": True}, idempotency_key=f"supplier-blocked:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                        continue
                    report = self._buy_supplier_intelligence(buyer, candidate, f"{self.clock.day}:{self.clock.tick}")
                    style_price = {"reliable": 4200, "cheap": 3700, "flexible": 3950}.get(candidate.negotiation_style, 4100)
                    offer = Proposal(type=ProposalType.OFFER, proposal_id=f"offer_{candidate.business_id}_{self.clock.day}_{self.clock.tick}", idempotency_key=f"offer:{candidate.business_id}:{self.clock.day}:{self.clock.tick}", agent_id=f"supplier_agent:{candidate.business_id}", business_id=buyer.business_id, counterparty_id=candidate.business_id, item=buyer.inventory_item, quantity=12, unit="bags", unit_price_cents=style_price, total_cents=style_price * 12, delivery_days=2 if candidate.negotiation_style != "flexible" else 1, public_rationale=f"{candidate.name} offered a {candidate.negotiation_style} supply option.", private_rationale="Offer was scored on price, delivery, and reliability before engine validation.")
                    self._emit("RFQSent", buyer.business_id, payload={"supplier_id": candidate.business_id, "item": buyer.inventory_item}, idempotency_key=f"rfq:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                    comparison = self.llm.compare_offers({"offers": [{"supplier_id": candidate.business_id, "price_cents": style_price, "reliability": candidate.reliability, "delivery_days": offer.delivery_days}]})
                    scored = score_offer(
                        {"price_cents": style_price, "delivery_days": offer.delivery_days, "reliability": candidate.reliability},
                        owner_preferences={"required_reliability": 0.7, "preferred_delivery_days": 2},
                    )
                    offer_record = {"offer": offer.model_dump(by_alias=True), "supplier_id": candidate.business_id, "score": scored["score"], "score_breakdown": scored, "reliability_report": report}
                    self.offers[offer.proposal_id] = offer_record
                    eligible_suppliers.append((candidate, offer_record))
                    self._emit("OfferCreated", buyer.business_id, payload={"supplier_id": candidate.business_id, "score": scored["score"], "score_breakdown": scored, "offer": offer.model_dump(by_alias=True), "claude_comparison": comparison.model_dump(), "reliability_report": report}, idempotency_key=f"offer-event:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                    if candidate.negotiation_style == "flexible":
                        counter = self.llm.negotiate_counter({"supplier_id": candidate.business_id, "seller_price_cents": style_price, "buyer_limit_cents": style_price - 50})
                        self._emit("CounterOfferReceived", buyer.business_id, payload={"supplier_id": candidate.business_id, "unit_price_cents": counter.unit_price_cents, "delivery_days": 1, "claude": counter.model_dump()}, idempotency_key=f"counter:{candidate.business_id}:{self.clock.day}:{self.clock.tick}")
                supplier_record = max(eligible_suppliers, key=lambda item: item[1]["score"], default=None)
                supplier = supplier_record[0] if supplier_record else None
                if supplier is None:
                    continue
                selected_price = {"reliable": 4200, "cheap": 3700, "flexible": 3950}.get(supplier.negotiation_style, 4100)
                proposal = Proposal(type=ProposalType.OFFER, proposal_id=f"tick_{self.clock.day}_{self.clock.tick}", idempotency_key=f"tick:{buyer.business_id}:{self.clock.day}:{self.clock.tick}", agent_id="procurement_agent", business_id=buyer.business_id, counterparty_id=supplier.business_id, item=buyer.inventory_item, quantity=12, unit="bags", unit_price_cents=selected_price, total_cents=selected_price * 12, delivery_days=2, public_rationale="Low inventory triggered autonomous replenishment.", private_rationale="Procurement scored price, delivery, and reliability; the deterministic engine will enforce reserve policy.")
                actions.append(self.submit_proposal(proposal).as_dict())
            self._emit("SchedulerTick", payload={"clock": self.clock.now(), "actions": len(actions)})
            return actions

    def tick(self) -> list[dict[str, Any]]:
        """Run one clock step through business agents when attached."""
        with self._lock:
            if self.agent_runtime is not None:
                return self.agent_runtime.tick()
            return self._legacy_tick()

