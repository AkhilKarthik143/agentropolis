"""Native, adapter-shaped procure-to-pay controls for the Hyphenate track.

The records are deliberately local and append-only for the demo.  They model
the control boundary without pretending that a private Hyphenate API is
connected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from threading import Lock


class MatchStatus(StrEnum):
    MATCHED = "matched"
    NEEDS_HUMAN = "needs_human"
    CONFLICT = "record_conflict"


class FinanceControlError(ValueError):
    pass


@dataclass(frozen=True)
class RoleAssignment:
    requester: str
    approver: str
    payer: str
    poster: str

    def validate(self) -> None:
        roles = {
            "requester": self.requester,
            "approver": self.approver,
            "payer": self.payer,
            "poster": self.poster,
        }
        if any(not identity.strip() for identity in roles.values()):
            raise FinanceControlError("every finance role needs an identity")
        if len(set(roles.values())) != len(roles):
            raise FinanceControlError("separation of duties: one identity cannot hold two roles")


@dataclass(frozen=True)
class PurchaseOrder:
    po_id: str
    business_id: str
    supplier_id: str
    item: str
    quantity: int
    unit_price_cents: int
    total_cents: int
    payment_terms: str
    cost_center: str
    roles: RoleAssignment


@dataclass(frozen=True)
class GoodsReceipt:
    receipt_id: str
    po_id: str
    quantity_received: int
    received_on: str


@dataclass(frozen=True)
class SupplierInvoice:
    invoice_id: str
    invoice_number: str
    po_id: str
    supplier_id: str
    amount_cents: int
    due_date: str
    payment_terms: str
    tax_cents: int
    cost_center: str


@dataclass(frozen=True)
class ThreeWayMatch:
    match_id: str
    po_id: str
    invoice_id: str
    receipt_id: str
    status: MatchStatus
    reasons: tuple[str, ...] = field(default_factory=tuple)


class FinanceControls:
    """Append-only PO/AP records and deterministic three-way matching."""

    def __init__(self) -> None:
        self.purchase_orders: list[PurchaseOrder] = []
        self.receipts: list[GoodsReceipt] = []
        self.invoices: list[SupplierInvoice] = []
        self.matches: list[ThreeWayMatch] = []
        self._lock = Lock()

    def create_po(self, po: PurchaseOrder) -> PurchaseOrder:
        po.roles.validate()
        if po.quantity <= 0 or po.unit_price_cents < 0 or po.total_cents != po.quantity * po.unit_price_cents:
            raise FinanceControlError("purchase order totals are invalid")
        with self._lock:
            existing = next((item for item in self.purchase_orders if item.po_id == po.po_id), None)
            if existing:
                return existing
            self.purchase_orders.append(po)
        return po

    def record_receipt(self, receipt: GoodsReceipt) -> GoodsReceipt:
        if receipt.quantity_received <= 0:
            raise FinanceControlError("goods receipt quantity must be positive")
        with self._lock:
            existing = next((item for item in self.receipts if item.receipt_id == receipt.receipt_id), None)
            if existing:
                return existing
            self.receipts.append(receipt)
        return receipt

    def record_invoice(self, invoice: SupplierInvoice) -> SupplierInvoice:
        if invoice.amount_cents <= 0 or invoice.tax_cents < 0:
            raise FinanceControlError("supplier invoice amount is invalid")
        with self._lock:
            existing = next((item for item in self.invoices if item.invoice_id == invoice.invoice_id), None)
            if existing:
                return existing
            if any(item.invoice_number == invoice.invoice_number for item in self.invoices):
                raise FinanceControlError("duplicate supplier invoice number")
            self.invoices.append(invoice)
        return invoice

    def match(self, match_id: str, po_id: str, invoice_id: str, receipt_id: str) -> ThreeWayMatch:
        po = next((item for item in self.purchase_orders if item.po_id == po_id), None)
        receipt = next((item for item in self.receipts if item.receipt_id == receipt_id), None)
        invoice = next((item for item in self.invoices if item.invoice_id == invoice_id), None)
        if not po or not receipt or not invoice:
            raise FinanceControlError("three-way match requires a PO, receipt, and invoice")
        reasons: list[str] = []
        if invoice.po_id != po.po_id:
            reasons.append("invoice references a different purchase order")
        if invoice.amount_cents != po.total_cents:
            reasons.append("invoice amount differs from purchase order")
        if receipt.quantity_received != po.quantity:
            reasons.append("received quantity differs from purchase order")
        status = MatchStatus.MATCHED if not reasons else MatchStatus.CONFLICT
        result = ThreeWayMatch(match_id, po.po_id, invoice.invoice_id, receipt.receipt_id, status, tuple(reasons))
        with self._lock:
            existing = next((item for item in self.matches if item.match_id == match_id), None)
            if existing:
                return existing
            self.matches.append(result)
        return result

    def snapshot(self) -> dict[str, list[dict]]:
        def serialize(value):
            data = asdict(value)
            if "roles" in data:
                data["roles"] = asdict(value.roles)
            if "status" in data and isinstance(data["status"], StrEnum):
                data["status"] = data["status"].value
            return data

        return {
            "purchase_orders": [serialize(item) for item in self.purchase_orders],
            "receipts": [serialize(item) for item in self.receipts],
            "invoices": [serialize(item) for item in self.invoices],
            "matches": [serialize(item) for item in self.matches],
        }


def default_roles(proposer: str) -> RoleAssignment:
    """Return distinct demo identities for a transaction."""

    return RoleAssignment(
        requester=proposer,
        approver="treasury_risk_agent",
        payer="payment_service",
        poster="accounting_service",
    )
