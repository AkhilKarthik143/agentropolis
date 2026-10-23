"""Append-only accounts-payable service backed by FinanceControls."""

from __future__ import annotations

from .controls import FinanceControls, GoodsReceipt, PurchaseOrder, SupplierInvoice, ThreeWayMatch


class AccountsPayableService:
    role = "accounts_payable"

    def __init__(self, controls: FinanceControls | None = None) -> None:
        self.controls = controls or FinanceControls()

    def create_purchase_order(self, purchase_order: PurchaseOrder) -> PurchaseOrder:
        return self.controls.create_po(purchase_order)

    def receive_goods(self, receipt: GoodsReceipt) -> GoodsReceipt:
        return self.controls.record_receipt(receipt)

    def record_supplier_invoice(self, invoice: SupplierInvoice) -> SupplierInvoice:
        return self.controls.record_invoice(invoice)

    def three_way_match(self, match_id: str, po_id: str, invoice_id: str, receipt_id: str) -> ThreeWayMatch:
        return self.controls.match(match_id, po_id, invoice_id, receipt_id)

    def duplicate_invoice_number(self, invoice_number: str) -> bool:
        return sum(item.invoice_number == invoice_number for item in self.controls.invoices) > 1
