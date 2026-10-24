"""Trusted economic commands. Agents choose; commands validate and execute.

A signed purchase reserves stock. Receipt creates AP/AR. Only a matched,
authorized obligation can settle. Every local command persists events and its
resulting state atomically, serialized by SQLite across worker processes.
"""

from __future__ import annotations

import hashlib
import json
import random
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from app.agents.llm_gateway import LLMGateway
from app.events.audit import verify_chain
from app.events.bus import EventBus
from app.events.schemas import EventEnvelope, Proposal, ProposalType, ValidationResult
from app.finance.approvals import ApprovalError, ApprovalManager
from app.finance.banking import BankError, MockBank
from app.finance.controls import (
    FinanceControlError,
    FinanceControls,
    GoodsReceipt,
    PurchaseOrder,
    SupplierInvoice,
    default_roles,
)
from app.finance.ledger import Account, JournalEntry, Ledger, LedgerLine
from app.finance.reconciliation import reconcile_business
from app.integrations.coinbase_x402 import MockX402, X402Rail
from app.integrations.crs_credit import MockCRSCredit
from app.security.gate import inspect_proposal
from .clock import SimClock
from .contracts import Contract, ContractStatus
from .inventory import Inventory
from .persistence import command, export_state, restore_state
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
    catalog: dict[str, dict] = field(default_factory=dict)
    allowed_suppliers: list[str] = field(default_factory=list)
    required_reliability: float = 0.7
    demand_per_tick: int = 0
    agent_roles: list[str] = field(default_factory=list)
    approval_threshold_cents: int = 150000
    inventory_value_cents: dict[str, int] = field(default_factory=dict)


@dataclass
class ProposalOutcome:
    status: str
    proposal_id: str
    deal_id: str | None = None
    approval_id: str | None = None
    reason: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return asdict(self)


def terms_hash(proposal: Proposal) -> str:
    # Include every term, including metadata. Approval cannot authorize an altered invoice.
    return hashlib.sha256(proposal.model_dump_json(by_alias=True).encode()).hexdigest()


class EconomyEngine:
    def __init__(
        self,
        bus=None,
        ledger=None,
        approvals=None,
        bank=None,
        seed=13,
        session_id="demo_001",
        controls=None,
        llm=None,
    ):
        self.bus = bus or EventBus()
        self.ledger = ledger or Ledger()
        self.approvals = approvals or ApprovalManager()
        self.bank = bank or MockBank()
        self.controls = controls or FinanceControls()
        self.llm = llm or LLMGateway(mode=os.getenv("AGENTROPOLIS_LLM_MODE", "replay"))
        self.credit = MockCRSCredit()
        self.x402 = X402Rail(MockX402())
        self.clock = SimClock()
        self.rng = random.Random(seed)
        self.session_id = session_id
        self.businesses = {}
        self.contracts = {}
        self.offers = {}
        self.payments = {}
        self._outcomes = {}
        self._pending = {}
        self._lock = RLock()
        self._version = 0
        self._command_depth = 0
        self._event_epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.agent_runtime = None
        self.seeded = False
        self.paused = True
        self.speed = 1.0
        self.faults = {}
        self.refresh()

    def refresh(self):
        stored = self.bus.store.load_state(self.session_id)
        if stored and stored[0] > self._version:
            self._version = stored[0]
            restore_state(self, stored[1])

    @command
    def checkpoint(self):
        return None

    def attach_agent_runtime(self, runtime):
        self.agent_runtime = runtime

    def _event_time(self):
        return self._event_epoch + timedelta(seconds=len(self.bus.replay()))

    def _emit(
        self,
        event_type,
        business_id=None,
        deal_id=None,
        proposal=None,
        payload=None,
        idempotency_key=None,
    ):
        data = dict(payload or {})
        if proposal:
            public = proposal.model_dump(mode="json", by_alias=True)
            public.pop("private_rationale", None)
            data.setdefault("proposal", public)
            data.setdefault(
                "public_rationale", proposal.public_rationale or proposal.rationale
            )

        def public_payload(value):
            if isinstance(value, dict):
                return {
                    key: public_payload(item)
                    for key, item in value.items()
                    if key != "private_rationale"
                }
            if isinstance(value, list):
                return [public_payload(item) for item in value]
            return value

        data = public_payload(data)
        return self.bus.append(
            EventEnvelope(
                ts=self._event_time(),
                type=event_type,
                session_id=self.session_id,
                business_id=business_id,
                deal_id=deal_id,
                correlation_id=deal_id or (proposal.deal_id if proposal else None),
                idempotency_key=f"{self.session_id}:{idempotency_key}"
                if idempotency_key
                else None,
                payload=data,
            )
        )

    def _transition_contract(self, contract, target, **kwargs):
        previous = contract.state
        contract.transition_state(target)
        self._emit(
            "StateTransition",
            contract.buyer_id,
            contract.contract_id,
            payload={
                "from_state": previous.value,
                "to_state": contract.state.value,
                **kwargs.get("payload", {}),
            },
            proposal=kwargs.get("proposal"),
        )

    @command
    def register_business(self, business, opening_cents=None):
        if business.business_id in self.businesses:
            return self.businesses[business.business_id]
        opening = opening_cents if opening_cents is not None else business.reserve_cents
        if min(opening, business.reserve_cents, business.spend_limit_cents) < 0:
            raise ValueError("cash and policies must be nonnegative")
        for item, quantity in business.capacity.items():
            if item not in business.inventory.quantities:
                business.inventory.add(item, quantity)
        for item in business.inventory.quantities:
            business.catalog.setdefault(
                item,
                {
                    "unit": "unit",
                    "unit_price_cents": 4000,
                    "cost_price_cents": 3000,
                    "lead_days": 2,
                    "kind": "physical",
                },
            )
        business.account_id = self.bank.create_account(business.business_id, opening)
        self.ledger.seed_cash(business.business_id, opening)
        business.inventory_value_cents = {
            item: q * int(business.catalog.get(item, {}).get("cost_price_cents", 0))
            for item, q in business.inventory.quantities.items()
        }
        value = sum(business.inventory_value_cents.values())
        if value:
            self.ledger.post(
                JournalEntry(
                    f"opening-stock:{business.business_id}",
                    business.business_id,
                    (
                        LedgerLine(Account.INVENTORY, value, business.business_id),
                        LedgerLine(Account.EQUITY, -value, business.business_id),
                    ),
                    idempotency_key=f"opening-stock:{business.business_id}",
                )
            )
        self.businesses[business.business_id] = business
        self._emit(
            "BusinessRegistered",
            business.business_id,
            payload={
                "business": self.business_snapshot(business.business_id),
                "bank_mode": self.bank.mode,
            },
            idempotency_key=f"business:{business.business_id}",
        )
        return business

    def committed_cents(self, business_id, exclude=None):
        return sum(
            c.total_cents
            for c in self.contracts.values()
            if c.buyer_id == business_id
            and c.contract_id != exclude
            and c.status not in {ContractStatus.DEFAULTED, ContractStatus.CANCELLED}
            and c.payment_state not in {"CONFIRMED", "RECONCILED"}
        )

    def business_snapshot(self, business_id):
        b = self.businesses[business_id]
        data = asdict(b)
        data["inventory"] = dict(b.inventory.quantities)
        data["reserved_inventory"] = {
            item: b.inventory.quantity(item) - b.inventory.available(item)
            for item in b.inventory.quantities
        }
        data["cash_cents"] = self.ledger.balance(business_id, Account.CASH)
        data["committed_cents"] = self.committed_cents(business_id)
        return data

    @command
    def update_business(self, business_id, changes):
        b = self.businesses[business_id]
        allowed = {
            "objective",
            "reserve_cents",
            "spend_limit_cents",
            "active",
            "agent_roles",
            "required_reliability",
            "demand_per_tick",
            "low_stock_threshold",
        }
        if set(changes) - allowed:
            raise ValueError("unsupported business policy field")
        for key, value in changes.items():
            setattr(b, key, value)
        self._emit("BusinessUpdated", business_id, payload={"changes": changes})
        return self.business_snapshot(business_id)

    def _validate(self, p):
        def fail(stage, code, message):
            return ValidationResult(
                ok=False, stage=stage, reason_code=code, message=message
            ), 0

        if p.session_id and p.session_id != self.session_id:
            return fail(
                "authorization",
                "SESSION_MISMATCH",
                "proposal belongs to another simulation",
            )
        if p.business_id not in self.businesses:
            return fail(
                "authorization", "UNKNOWN_BUSINESS", "unknown proposing business"
            )
        buyer = self.businesses[p.business_id]
        if not buyer.active:
            return fail("authorization", "BUSINESS_PAUSED", "business is paused")
        if ":" in p.agent_id and p.agent_id.split(":", 1)[1] != p.business_id:
            return fail(
                "authorization",
                "AGENT_SCOPE",
                "agent does not belong to purchasing business",
            )
        if p.agent_id.split(":")[0] not in {
            "procurement",
            "procurement_agent",
            "payments_agent",
            "payments",
            "human_operator",
            "seed_service",
        }:
            return fail(
                "authorization",
                "ROLE_FORBIDDEN",
                "agent cannot authorize a purchase proposal",
            )
        if p.proposal_type not in {ProposalType.OFFER, ProposalType.COUNTER_OFFER}:
            return fail(
                "schema",
                "UNSUPPORTED_PROPOSAL",
                "only offers and counteroffers are accepted",
            )
        seller = self.businesses.get(p.counterparty_id)
        if not seller or seller is buyer or not seller.active:
            return fail(
                "counterparty", "COUNTERPARTY_UNAVAILABLE", "counterparty unavailable"
            )
        if p.deal_id in self.contracts:
            return fail("authorization", "STALE_OFFER", "deal already has a contract")
        if not p.item or not p.quantity or p.unit_price_cents is None:
            return fail(
                "schema",
                "INCOMPLETE_OFFER",
                "item, quantity, and unit price are required",
            )
        amount = p.quantity * p.unit_price_cents
        if amount <= 0 or (p.total_cents is not None and p.total_cents != amount):
            return fail(
                "schema", "TOTAL_MISMATCH", "total must equal quantity times unit price"
            )
        if (
            buyer.allowed_suppliers
            and seller.business_id not in buyer.allowed_suppliers
        ):
            return fail(
                "counterparty", "UNAPPROVED_SUPPLIER", "supplier is not permitted"
            )
        if (
            seller.credit_status == "blocked"
            or seller.reliability < buyer.required_reliability
        ):
            return fail("counterparty", "LOW_RELIABILITY", "supplier fails risk policy")
        cash = self.ledger.balance(
            buyer.business_id, Account.CASH
        ) - self.committed_cents(buyer.business_id)
        if cash - amount < buyer.reserve_cents:
            return ValidationResult(
                ok=False,
                stage="cash_and_reserve",
                reason_code="RESERVE_VIOLATION",
                message="purchase breaches reserve after existing commitments",
            ), amount
        if amount > buyer.spend_limit_cents:
            return ValidationResult(
                ok=False,
                stage="spend_limit",
                reason_code="SPEND_LIMIT",
                message="purchase exceeds spend limit",
            ), amount
        if seller.inventory.available(p.item) < p.quantity:
            return fail(
                "inventory",
                "INSUFFICIENT_STOCK",
                "supplier cannot reserve the requested quantity",
            )
        product = seller.catalog.get(p.item, {})
        if p.unit_price_cents < int(product.get("cost_price_cents", 0)):
            return fail(
                "counterparty",
                "BELOW_COST",
                "supplier offer is below its authorized cost floor",
            )
        if p.unit and product.get("unit") and p.unit != product["unit"]:
            return fail(
                "schema", "UNIT_MISMATCH", "offer unit differs from product catalog"
            )
        return ValidationResult(
            ok=True,
            stage="validated",
            message="authorization, available stock, liquidity, and risk passed",
            details={"amount_cents": amount},
        ), amount

    @command
    def submit_proposal(self, proposal):
        if proposal.idempotency_key in self._outcomes:
            return self._outcomes[proposal.idempotency_key]
        proposal = proposal.model_copy(deep=True)
        gate = inspect_proposal(proposal)
        if not gate.allowed:
            result = ProposalOutcome(
                "blocked",
                proposal.proposal_id,
                reason=gate.reason,
                validation={"reason_code": gate.code},
            )
            self._emit(
                "ACTION_BLOCKED",
                proposal.business_id,
                proposal.deal_id,
                proposal=proposal,
                payload={"reason": gate.reason, "code": gate.code},
            )
        else:
            valid, amount = self._validate(proposal)
            if not valid.ok:
                result = ProposalOutcome(
                    "rejected",
                    proposal.proposal_id,
                    reason=valid.message,
                    validation=valid.model_dump(),
                )
                self._emit(
                    "ProposalRejected",
                    proposal.business_id,
                    proposal.deal_id,
                    proposal=proposal,
                    payload={"validation": valid.model_dump()},
                )
            else:
                buyer = self.businesses[proposal.business_id]
                if amount >= min(
                    self.approvals.threshold_cents, buyer.approval_threshold_cents
                ):
                    approval = self.approvals.request(
                        proposal.proposal_id,
                        proposal.business_id,
                        amount,
                        proposal.agent_id,
                        reason="spending threshold requires human approval",
                        needs_human=True,
                    )
                    approval.terms_hash = terms_hash(proposal)
                    self._pending[approval.approval_id] = proposal
                    self._emit(
                        "ApprovalRequested",
                        proposal.business_id,
                        proposal.deal_id,
                        proposal=proposal,
                        payload={
                            "approval_id": approval.approval_id,
                            "terms_hash": approval.terms_hash,
                            "amount_cents": amount,
                        },
                    )
                    result = ProposalOutcome(
                        "approval_required",
                        proposal.proposal_id,
                        approval_id=approval.approval_id,
                        validation=valid.model_dump(),
                    )
                else:
                    result = self._execute(proposal, valid, amount)
        self._outcomes[proposal.idempotency_key] = result
        return result

    def _execute(self, p, validation, amount):
        supplier = self.businesses[p.counterparty_id]
        deal_id = p.deal_id or f"deal_{len(self.contracts) + 1:04d}"
        product = supplier.catalog.get(p.item, {})
        reservation_id = f"reservation:{deal_id}"
        supplier.inventory.reserve(reservation_id, p.item, p.quantity)
        po_id = f"po:{deal_id}"
        roles = default_roles(p.agent_id)
        self.controls.create_po(
            PurchaseOrder(
                po_id,
                p.business_id,
                p.counterparty_id,
                p.item,
                p.quantity,
                p.unit_price_cents,
                amount,
                p.payment_terms or "on receipt",
                "OPERATIONS",
                roles,
            )
        )
        c = Contract(
            deal_id,
            p.business_id,
            p.counterparty_id,
            p.item,
            p.quantity,
            p.unit_price_cents,
            amount,
            p.delivery_days or 0,
            ContractStatus.ACCEPTED,
            p.proposal_id,
            p.public_rationale or p.rationale,
            supplier.reliability,
            EconomyState.CONTRACTED,
            unit=p.unit or product.get("unit", "unit"),
            created_tick=self.clock.tick,
            due_tick=self.clock.tick + max(1, p.delivery_days or 1),
            reservation_id=reservation_id,
            payment_id=f"payment:{deal_id}",
            po_id=po_id,
            approved_terms_hash=terms_hash(p),
            recovery=bool(p.metadata.get("recovery")),
            kind=product.get("kind", "physical"),
            cost_price_cents=int(product.get("cost_price_cents", 0)),
        )
        self.contracts[deal_id] = c
        self.payments[c.payment_id] = {
            "payment_id": c.payment_id,
            "obligation_id": deal_id,
            "payer": c.buyer_id,
            "payee": c.supplier_id,
            "amount_cents": amount,
            "currency": "USD",
            "rail": self.bank.mode,
            "status": "APPROVED",
            "idempotency_key": f"payment:{self.session_id}:{p.idempotency_key}",
            "authorization_hash": c.approved_terms_hash,
            "provider_transaction_id": None,
            "attempts": 0,
            "reconciliation_status": "pending",
        }
        self._emit(
            "ContractAccepted",
            c.buyer_id,
            deal_id,
            proposal=p,
            payload={"contract": self.contract_snapshot(deal_id)},
        )
        self._emit(
            "InventoryReserved",
            c.supplier_id,
            deal_id,
            payload={
                "item": c.item,
                "quantity": c.quantity,
                "reservation_id": reservation_id,
            },
        )
        self._transition_contract(c, EconomyState.AWAITING_DELIVERY)
        self._emit(
            "GoodsAwaitingDelivery",
            c.buyer_id,
            deal_id,
            payload={"due_tick": c.due_tick, "quantity": c.quantity},
        )
        return ProposalOutcome(
            "executed",
            p.proposal_id,
            deal_id=deal_id,
            validation=validation.model_dump(),
        )

    @command
    def resolve_approval(self, approval_id, approver, granted):
        if approver != "human_operator":
            raise ApprovalError(
                "protected approval requires the authenticated human operator"
            )
        p = self._pending.get(approval_id)
        if p is None:
            raise ApprovalError("approval is missing or already resolved")
        request = self.approvals.requests[approval_id]
        if getattr(request, "terms_hash", "") != terms_hash(p):
            raise ApprovalError("approved terms changed; a new approval is required")
        self.approvals.decide(
            approval_id, approver, granted, poster="accounting_service"
        )
        self._pending.pop(approval_id)
        self._emit(
            "ApprovalGranted" if granted else "ApprovalDenied",
            p.business_id,
            p.deal_id,
            payload={"approval_id": approval_id, "approver": approver},
        )
        if granted:
            valid, amount = self._validate(p)
            result = (
                self._execute(p, valid, amount)
                if valid.ok
                else ProposalOutcome(
                    "rejected",
                    p.proposal_id,
                    reason=valid.message,
                    validation=valid.model_dump(),
                )
            )
        else:
            result = ProposalOutcome(
                "denied",
                p.proposal_id,
                approval_id=approval_id,
                reason="human approval denied",
            )
        self._outcomes[p.idempotency_key] = result
        return result

    def contract_snapshot(self, contract_id):
        c = self.contracts[contract_id]
        data = asdict(c)
        data["status"] = c.status.value
        data["state"] = c.state.value
        data["received_quantity"] = c.delivered_quantity
        data["reserved_quantity"] = (
            self.businesses[c.supplier_id]
            .inventory.reservations.get(c.reservation_id, {})
            .get("quantity", 0)
        )
        return data

    @command
    def ship_contract(self, deal_id):
        c = self.contracts[deal_id]
        if c.fulfillment_state in {"SHIPPED", "PARTIALLY_RECEIVED", "RECEIVED"}:
            return self.contract_snapshot(deal_id)
        if (
            c.fulfillment_state != "RESERVED"
            or not self.businesses[c.supplier_id].active
        ):
            raise ValueError("contract cannot ship")
        c.fulfillment_state = "SHIPPED"
        self._emit(
            "GoodsShipped",
            c.buyer_id,
            deal_id,
            payload={"supplier_id": c.supplier_id, "quantity": c.quantity},
        )
        return self.contract_snapshot(deal_id)

    @command
    def deliver_contract(self, deal_id, quantity=None):
        c = self.contracts.get(deal_id)
        if c is None:
            raise ValueError("contract not found")
        if c.fulfillment_state == "RECEIVED":
            return self.contract_snapshot(deal_id)
        if c.fulfillment_state not in {"RESERVED", "SHIPPED", "PARTIALLY_RECEIVED"}:
            raise ValueError("contract is not eligible for receipt")
        if not self.businesses[c.supplier_id].active:
            raise ValueError("supplier is unavailable")
        remaining = c.quantity - c.delivered_quantity
        quantity = remaining if quantity is None else quantity
        if type(quantity) is not int or quantity <= 0 or quantity > remaining:
            raise ValueError("invalid receipt quantity")
        if c.fulfillment_state == "RESERVED":
            self.ship_contract(deal_id)
        supplier = self.businesses[c.supplier_id]
        buyer = self.businesses[c.buyer_id]
        stock_value = supplier.inventory_value_cents.get(c.item, 0)
        cost = stock_value * quantity // max(1, supplier.inventory.quantity(c.item))
        supplier.inventory.fulfill(c.reservation_id, quantity)
        supplier.inventory_value_cents[c.item] = stock_value - cost
        amount = quantity * c.unit_price_cents
        if c.kind != "service":
            buyer.inventory.add(c.item, quantity)
            buyer.inventory_value_cents[c.item] = (
                buyer.inventory_value_cents.get(c.item, 0) + amount
            )
        suffix = f"{deal_id}:{c.delivered_quantity + quantity}"
        self.ledger.post(
            JournalEntry(
                f"receipt-buyer:{suffix}",
                c.buyer_id,
                (
                    LedgerLine(
                        Account.SERVICE_EXPENSE
                        if c.kind == "service"
                        else Account.INVENTORY,
                        amount,
                        c.buyer_id,
                    ),
                    LedgerLine(Account.ACCOUNTS_PAYABLE, -amount, c.buyer_id),
                ),
                memo="Verified goods/service receipt on credit",
                idempotency_key=f"receipt-buyer:{suffix}",
            )
        )
        seller_lines = [
            LedgerLine(Account.ACCOUNTS_RECEIVABLE, amount, c.supplier_id),
            LedgerLine(Account.REVENUE, -amount, c.supplier_id),
        ]
        if cost:
            seller_lines.extend(
                [
                    LedgerLine(Account.COGS, cost, c.supplier_id),
                    LedgerLine(Account.INVENTORY, -cost, c.supplier_id),
                ]
            )
        self.ledger.post(
            JournalEntry(
                f"receipt-seller:{suffix}",
                c.supplier_id,
                tuple(seller_lines),
                memo="Delivery, revenue and inventory cost",
                idempotency_key=f"receipt-seller:{suffix}",
            )
        )
        c.delivered_quantity += quantity
        c.fulfillment_state = (
            "RECEIVED" if c.delivered_quantity == c.quantity else "PARTIALLY_RECEIVED"
        )
        c.status = (
            ContractStatus.DELIVERED
            if c.fulfillment_state == "RECEIVED"
            else ContractStatus.PARTIAL
        )
        self._emit(
            "GoodsReceived",
            c.buyer_id,
            deal_id,
            payload={
                "quantity": quantity,
                "received_quantity": c.delivered_quantity,
                "item": c.item,
            },
        )
        self._emit(
            "InventoryReceiptConfirmed",
            c.buyer_id,
            deal_id,
            payload={"quantity": quantity, "item": c.item, "mode": "verified_receipt"},
        )
        if c.fulfillment_state == "RECEIVED":
            c.receipt_id = f"receipt:{deal_id}"
            c.invoice_id = f"invoice:{deal_id}"
            self.controls.record_receipt(
                GoodsReceipt(c.receipt_id, c.po_id, c.quantity, self.clock.now())
            )
            self.controls.record_invoice(
                SupplierInvoice(
                    c.invoice_id,
                    f"INV-{deal_id}",
                    c.po_id,
                    c.supplier_id,
                    c.total_cents,
                    self.clock.now(),
                    "on receipt",
                    0,
                    "OPERATIONS",
                )
            )
            match = self.controls.match(
                f"match:{deal_id}", c.po_id, c.invoice_id, c.receipt_id
            )
            self._transition_contract(c, EconomyState.DELIVERED)
            self._emit(
                "InvoiceMatched",
                c.buyer_id,
                deal_id,
                payload={"invoice_id": c.invoice_id, "match": asdict(match)},
            )
            if c.recovery:
                self._emit(
                    "INVENTORY_RECOVERED",
                    c.buyer_id,
                    deal_id,
                    payload={"item": c.item, "quantity": c.quantity},
                )
        return self.contract_snapshot(deal_id)

    @command
    def _prepare_payment(self, deal_id):
        c = self.contracts[deal_id]
        p = self.payments[c.payment_id]
        if p["status"] in {"SUBMITTED", "UNCERTAIN", "CONFIRMED", "RECONCILED"}:
            return dict(p), False
        if c.fulfillment_state != "RECEIVED":
            raise ValueError("payment requires a verified full receipt")
        if self.faults.get(f"invoice:{deal_id}"):
            raise ValueError("invoice held for risk review")
        match = self.controls.match(
            f"payment-match:{deal_id}", c.po_id, c.invoice_id, c.receipt_id
        )
        if match.status.value != "matched":
            raise ValueError("invoice is not matched")
        if (
            p["authorization_hash"] != c.approved_terms_hash
            or p["amount_cents"] != c.total_cents
            or p["payee"] != c.supplier_id
        ):
            raise ValueError("payment terms differ from authorization")
        b = self.businesses[c.buyer_id]
        if (
            not b.active
            or self.ledger.balance(c.buyer_id, Account.CASH)
            - p["amount_cents"]
            - self.committed_cents(c.buyer_id, deal_id)
            < b.reserve_cents
        ):
            raise ValueError("payment would breach liquidity policy")
        p.update(status="SUBMITTED", attempts=p["attempts"] + 1)
        c.payment_state = "SUBMITTED"
        self._emit("PaymentSubmitted", c.buyer_id, deal_id, payload=dict(p))
        return dict(p), True

    def pay_contract(self, deal_id):
        payment, submit = self._prepare_payment(deal_id)
        if not submit:
            return payment
        if self.bank.mode == "mock":
            return self._settle_mock_payment(deal_id)
        # Never guess a sandbox settlement after a transport timeout. Only a
        # positive provider confirmation can be posted by confirm_external_payment.
        try:
            c = self.contracts[deal_id]
            tx = self.bank.transfer(
                self.businesses[c.buyer_id].account_id,
                self.businesses[c.supplier_id].account_id,
                c.total_cents,
                c.item,
                payment["idempotency_key"],
            )
        except Exception as exc:
            return self._payment_failure(deal_id, "UNCERTAIN", type(exc).__name__)
        return self.confirm_external_payment(deal_id, tx)

    @command
    def _settle_mock_payment(self, deal_id):
        c = self.contracts[deal_id]
        p = self.payments[c.payment_id]
        if p["status"] != "SUBMITTED":
            return dict(p)
        if self.faults.pop(f"payment:{c.buyer_id}", False):
            return self._payment_failure(
                deal_id, "FAILED", "injected sandbox payment failure"
            )
        try:
            tx = self.bank.transfer(
                self.businesses[c.buyer_id].account_id,
                self.businesses[c.supplier_id].account_id,
                c.total_cents,
                c.item,
                p["idempotency_key"],
            )
        except BankError as exc:
            return self._payment_failure(deal_id, "FAILED", str(exc))
        return self._post_settlement(c, p, tx)

    @command
    def confirm_external_payment(self, deal_id, tx):
        c = self.contracts[deal_id]
        p = self.payments[c.payment_id]
        if p["status"] in {"CONFIRMED", "RECONCILED"}:
            return dict(p)
        if p["status"] not in {"SUBMITTED", "UNCERTAIN"}:
            raise ValueError("payment was not submitted")
        if getattr(tx, "status", "") not in {"completed", "confirmed", "executed"}:
            return self._payment_failure(
                deal_id, "UNCERTAIN", "provider has not confirmed settlement"
            )
        return self._post_settlement(c, p, tx)

    def _post_settlement(self, c, p, tx):
        if (
            tx.amount_cents != c.total_cents
            or tx.from_account != self.businesses[c.buyer_id].account_id
            or tx.to_account != self.businesses[c.supplier_id].account_id
        ):
            raise ValueError("provider result differs from authorized payment")
        self.ledger.post(
            JournalEntry(
                f"payment-buyer:{c.contract_id}",
                c.buyer_id,
                (
                    LedgerLine(Account.ACCOUNTS_PAYABLE, c.total_cents, c.buyer_id),
                    LedgerLine(Account.CASH, -c.total_cents, c.buyer_id),
                ),
                idempotency_key=f"payment-buyer:{c.contract_id}",
            )
        )
        self.ledger.post(
            JournalEntry(
                f"payment-seller:{c.contract_id}",
                c.supplier_id,
                (
                    LedgerLine(Account.CASH, c.total_cents, c.supplier_id),
                    LedgerLine(
                        Account.ACCOUNTS_RECEIVABLE, -c.total_cents, c.supplier_id
                    ),
                ),
                idempotency_key=f"payment-seller:{c.contract_id}",
            )
        )
        p.update(status="CONFIRMED", provider_transaction_id=tx.transaction_id)
        c.payment_state = "CONFIRMED"
        c.status = ContractStatus.PAID
        self._emit("PaymentConfirmed", c.buyer_id, c.contract_id, payload=dict(p))
        self._emit(
            "PaymentRecorded",
            c.buyer_id,
            c.contract_id,
            payload={
                "transaction_id": tx.transaction_id,
                "amount_cents": c.total_cents,
                "rail": self.bank.mode,
            },
        )
        self._emit(
            "LedgerPosted",
            c.buyer_id,
            c.contract_id,
            payload={
                "balanced": self.ledger.is_balanced(c.buyer_id)
                and self.ledger.is_balanced(c.supplier_id)
            },
        )
        return dict(p)

    @command
    def _payment_failure(self, deal_id, status, reason):
        c = self.contracts[deal_id]
        p = self.payments[c.payment_id]
        p.update(status=status, error=reason)
        c.payment_state = status
        self._emit(
            "PaymentFailed" if status == "FAILED" else "PaymentUncertain",
            c.buyer_id,
            deal_id,
            payload=dict(p),
        )
        return dict(p)

    @command
    def reconcile_payment(self, payment_id):
        p = self.payments[payment_id]
        c = self.contracts[p["obligation_id"]]
        if p["status"] == "RECONCILED":
            return dict(p)
        if p["status"] != "CONFIRMED":
            raise ValueError("only confirmed settlement can reconcile")
        tx = next(
            (
                t
                for t in self.bank.history()
                if t.transaction_id == p["provider_transaction_id"]
            ),
            None,
        )
        results = [
            reconcile_business(
                bid, self.businesses[bid].account_id, self.ledger, self.bank
            )
            for bid in (c.buyer_id, c.supplier_id)
        ]
        if (
            tx is None
            or tx.amount_cents != p["amount_cents"]
            or not all(r.ok for r in results)
        ):
            p["reconciliation_status"] = "conflict"
            self._emit(
                "ReconciliationConflict",
                c.buyer_id,
                c.contract_id,
                payload={"payment_id": payment_id},
            )
            return dict(p)
        p.update(status="RECONCILED", reconciliation_status="matched")
        c.payment_state = "RECONCILED"
        self._emit(
            "Reconciled",
            c.buyer_id,
            c.contract_id,
            payload={
                "payment_id": payment_id,
                "status": "matched",
                "entities": [asdict(r) for r in results],
            },
        )
        return dict(p)

    @command
    def consume_inventory(self, business_id, item, quantity):
        b = self.businesses[business_id]
        on_hand = b.inventory.quantity(item)
        if quantity > on_hand:
            raise ValueError("insufficient stock for demand")
        inventory_value = b.inventory_value_cents.get(item, 0)
        value = inventory_value * quantity // max(1, on_hand)
        b.inventory.consume(item, quantity)
        b.inventory_value_cents[item] = inventory_value - value
        if value:
            self.ledger.post(
                JournalEntry(
                    f"consumption:{business_id}:{self.clock.tick}:{len(self.ledger.entries)}",
                    business_id,
                    (
                        LedgerLine(Account.COGS, value, business_id),
                        LedgerLine(Account.INVENTORY, -value, business_id),
                    ),
                    memo="Inventory consumed by operations",
                )
            )
        self._emit(
            "DemandTick", business_id, payload={"item": item, "quantity": quantity}
        )

    @command
    def advance_clock(self):
        self.clock.advance()
        for b in self.businesses.values():
            if b.active and b.demand_per_tick > 0:
                quantity = min(
                    b.demand_per_tick, b.inventory.available(b.inventory_item)
                )
                if quantity:
                    self.consume_inventory(b.business_id, b.inventory_item, quantity)
        return self.clock.now()

    @command
    def set_clock(self, *, paused=None, speed=None):
        if paused is not None:
            self.paused = paused
        if speed is not None:
            if not 0.25 <= speed <= 4:
                raise ValueError("speed must be between 0.25 and 4")
            self.speed = speed
        self._emit("ClockChanged", payload={"paused": self.paused, "speed": self.speed})
        return {
            "paused": self.paused,
            "speed": self.speed,
            "tick": self.clock.tick,
            "day": self.clock.day,
        }

    @command
    def shock(self, shock_type, supplier_id=None):
        kind = {
            "supplier_bankrupt": "supplier_bankruptcy",
            "shortage": "inventory_shortage",
            "failed_payment": "payment_failure",
            "logistics_failure": "delivery_failure",
        }.get(shock_type, shock_type)
        buyer = next(
            (b for b in self.businesses.values() if b.role == "buyer" and b.active),
            None,
        )
        if not buyer:
            raise ValueError("no active buyer")
        affected = []
        self._emit(
            "ShockInjected",
            buyer.business_id,
            payload={
                "shock_type": kind,
                "supplier_id": supplier_id,
                "clock": self.clock.now(),
            },
        )
        if kind in {"supplier_bankruptcy", "delivery_failure"}:
            supplier_id = supplier_id or next(
                (
                    c.supplier_id
                    for c in self.contracts.values()
                    if c.fulfillment_state
                    in {"RESERVED", "SHIPPED", "PARTIALLY_RECEIVED"}
                ),
                None,
            )
            if supplier_id not in self.businesses:
                raise ValueError("supplier not found")
            if kind == "supplier_bankruptcy":
                self.businesses[supplier_id].active = False
            for c in self.contracts.values():
                if c.supplier_id != supplier_id or c.fulfillment_state not in {
                    "RESERVED",
                    "SHIPPED",
                    "PARTIALLY_RECEIVED",
                }:
                    continue
                self.businesses[supplier_id].inventory.release(c.reservation_id)
                c.fulfillment_state = "FAILED"
                c.status = ContractStatus.DEFAULTED
                if c.payment_state == "APPROVED":
                    c.payment_state = "CANCELLED"
                    self.payments[c.payment_id]["status"] = "CANCELLED"
                self._emit(
                    "SupplierDefaulted"
                    if kind == "supplier_bankruptcy"
                    else "DeliveryFailed",
                    c.buyer_id,
                    c.contract_id,
                    payload={
                        "supplier_id": supplier_id,
                        "remaining_quantity": c.quantity - c.delivered_quantity,
                        "item": c.item,
                    },
                )
                self._emit(
                    "RecoveryRequested",
                    c.buyer_id,
                    c.contract_id,
                    payload={
                        "failed_supplier": supplier_id,
                        "item": c.item,
                        "quantity": c.quantity - c.delivered_quantity,
                        "shock_type": kind,
                    },
                )
                affected.append(c.contract_id)
            if not affected:
                self._emit(
                    "RecoveryRequested",
                    buyer.business_id,
                    payload={
                        "failed_supplier": supplier_id,
                        "item": buyer.inventory_item,
                        "quantity": max(1, buyer.low_stock_threshold * 2),
                        "shock_type": kind,
                    },
                )
        elif kind == "demand_spike":
            buyer.demand_per_tick = max(1, buyer.demand_per_tick) * 3
            self._emit(
                "DemandChanged",
                buyer.business_id,
                payload={"demand_per_tick": buyer.demand_per_tick},
            )
        elif kind == "inventory_shortage":
            candidates = [
                b
                for b in self.businesses.values()
                if b.role == "supplier"
                and (supplier_id is None or b.business_id == supplier_id)
            ]
            for b in candidates:
                for item in list(b.inventory.quantities):
                    available = b.inventory.available(item)
                    if available:
                        self.consume_inventory(b.business_id, item, available)
            self._emit(
                "RecoveryRequested",
                buyer.business_id,
                payload={
                    "item": buyer.inventory_item,
                    "quantity": 12,
                    "shock_type": kind,
                },
            )
        elif kind == "liquidity_crisis":
            buyer.reserve_cents = self.ledger.balance(buyer.business_id, Account.CASH)
            self._emit(
                "RiskAlert",
                buyer.business_id,
                payload={
                    "reason": "liquidity locked by emergency reserve",
                    "reserve_cents": buyer.reserve_cents,
                },
            )
        elif kind == "payment_failure":
            self.faults[f"payment:{buyer.business_id}"] = True
            self._emit(
                "PaymentFailureArmed",
                buyer.business_id,
                payload={"applies_to": "next sandbox payment"},
            )
        elif kind == "suspicious_invoice":
            c = next(
                (
                    c
                    for c in reversed(list(self.contracts.values()))
                    if c.buyer_id == buyer.business_id
                    and c.payment_state not in {"CONFIRMED", "RECONCILED", "CANCELLED"}
                ),
                None,
            )
            if c:
                self.faults[f"invoice:{c.contract_id}"] = True
                self._emit(
                    "InvoiceMismatch",
                    buyer.business_id,
                    c.contract_id,
                    payload={
                        "reason": "unverified supplier banking instruction",
                        "payment_blocked": True,
                    },
                )
                self._emit(
                    "RiskAlert",
                    buyer.business_id,
                    c.contract_id,
                    payload={"reason": "invoice held for controller review"},
                )
        else:
            raise ValueError("unsupported shock")
        return {
            "ok": True,
            "shock_type": kind,
            "affected_contracts": affected,
            "recovery_status": "agents_notified"
            if kind in {"supplier_bankruptcy", "delivery_failure", "inventory_shortage"}
            else "condition_applied",
        }

    def summary(self):
        self.refresh()
        events = self.bus.replay()
        payload = {
            "schema_version": 2,
            "simulation_id": self.session_id,
            "mode": "LOCAL SIMULATION"
            if self.bank.mode == "mock"
            else self.bank.mode.upper(),
            "clock": self.clock.now(),
            "clock_control": {
                "paused": self.paused,
                "speed": self.speed,
                "tick": self.clock.tick,
                "day": self.clock.day,
            },
            "businesses": [self.business_snapshot(bid) for bid in self.businesses],
            "offers": list(self.offers.values()),
            "contracts": [self.contract_snapshot(cid) for cid in self.contracts],
            "payments": list(self.payments.values()),
            "approvals": self.approvals.snapshot(),
            "ledger": self.ledger.snapshot(),
            "trial_balance": self.ledger.trial_balance(),
            "ledger_proof": self.ledger.proof(),
            "finance": self.controls.snapshot(),
            "reconciliation": [
                asdict(
                    reconcile_business(
                        b.business_id, b.account_id, self.ledger, self.bank
                    )
                )
                for b in self.businesses.values()
            ],
            "audit": verify_chain(events),
            "events": [e.model_dump(mode="json") for e in events[-60:]],
            "integration_status": {
                "banking": self.bank.mode,
                "reasoning": self.llm.mode,
                "transport": "local durable queue",
                "x402": self.x402.mode,
            },
        }
        if self.agent_runtime:
            payload["agent_runtime"] = self.agent_runtime.snapshot()
            from .scoring import score_offer

            visible_offers = []
            for negotiation in payload["agent_runtime"].get("negotiations", []):
                for seller_id, quote in negotiation.get("offers", {}).items():
                    scored = score_offer(
                        {
                            "price_cents": quote["unit_price_cents"],
                            "delivery_days": quote["delivery_days"],
                            "reliability": quote["reliability"],
                        },
                        owner_preferences={
                            "required_reliability": self.businesses[
                                negotiation["business_id"]
                            ].required_reliability
                        },
                    )
                    visible_offers.append(
                        {
                            "supplier_id": seller_id,
                            "negotiation_id": negotiation["negotiation_id"],
                            "business_id": negotiation["business_id"],
                            "score": scored["score"],
                            "score_breakdown": scored,
                            "offer": {
                                "proposal_id": f"{negotiation['negotiation_id']}:{seller_id}",
                                **quote,
                                "public_rationale": quote.get(
                                    "rationale",
                                    "Independent supplier quote from current cost and available stock",
                                ),
                            },
                            "reliability_report": {
                                "mode": "simulation",
                                "status": "local policy review",
                            },
                        }
                    )
            payload["offers"] = visible_offers
        return payload

    def audit_verification(self):
        return verify_chain(self.bus.replay())

    def ledger_proof(self, business_id=None):
        return self.ledger.proof(business_id)

    def tick(self):
        if self.agent_runtime is None:
            from app.orchestration.runtime import AgentRuntime

            self.attach_agent_runtime(AgentRuntime(self))
        actions = self.agent_runtime.tick()
        self.checkpoint()
        return actions
