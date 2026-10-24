"""Explicit JSON persistence; no executable pickle or serialized credentials."""

from dataclasses import asdict
from functools import wraps
from app.economy.inventory import Inventory
from app.economy.contracts import Contract, ContractStatus
from app.economy.state_machine import EconomyState
from app.finance.approvals import ApprovalRequest, ApprovalStatus
from app.finance.banking import BankTransaction
from app.finance.controls import (
    PurchaseOrder,
    GoodsReceipt,
    SupplierInvoice,
    ThreeWayMatch,
    RoleAssignment,
    MatchStatus,
)
from app.finance.ledger import JournalEntry, LedgerLine, Account, Ledger
from app.events.schemas import Proposal


def export_state(engine):
    return {
        "schema_version": 2,
        "seeded": engine.seeded,
        "businesses": [asdict(b) for b in engine.businesses.values()],
        "contracts": [asdict(c) for c in engine.contracts.values()],
        "offers": engine.offers,
        "payments": engine.payments,
        "ledger": engine.ledger.snapshot(),
        "finance": engine.controls.snapshot(),
        "bank": {
            "mode": engine.bank.mode,
            "accounts": dict(getattr(engine.bank, "accounts", {})),
            "transactions": [asdict(t) for t in engine.bank.history()],
        },
        "approvals": [asdict(r) for r in engine.approvals.requests.values()],
        "pending": {
            k: v.model_dump(mode="json", by_alias=True)
            for k, v in engine._pending.items()
        },
        "outcomes": {k: v.as_dict() for k, v in engine._outcomes.items()},
        "clock": asdict(engine.clock),
        "paused": engine.paused,
        "speed": engine.speed,
        "faults": engine.faults,
    }


def restore_state(engine, data):
    from app.economy.engine import Business, ProposalOutcome

    engine.seeded = data.get("seeded", False)
    engine.businesses = {}
    for row in data["businesses"]:
        row = dict(row)
        row["inventory"] = Inventory(**row["inventory"])
        engine.businesses[row["business_id"]] = Business(**row)
    engine.contracts = {}
    for row in data["contracts"]:
        row = dict(row)
        row["status"] = ContractStatus(row["status"])
        row["state"] = EconomyState(row["state"])
        engine.contracts[row["contract_id"]] = Contract(**row)
    engine.offers = data["offers"]
    engine.payments = data.get("payments", {})
    engine.ledger = Ledger()
    for row in data["ledger"]:
        row = dict(row)
        row["lines"] = tuple(
            LedgerLine(**{**line, "account": Account(line["account"])})
            for line in row["lines"]
        )
        engine.ledger.post(JournalEntry(**row))
    bank = data["bank"]
    if engine.bank.mode == "mock":
        engine.bank.accounts = bank["accounts"]
        engine.bank.transactions = [BankTransaction(**t) for t in bank["transactions"]]
        engine.bank._idempotency = {
            t.idempotency_key: t for t in engine.bank.transactions
        }
        engine.bank._counter = len(engine.bank.transactions)
    for attr, cls in [
        ("purchase_orders", PurchaseOrder),
        ("receipts", GoodsReceipt),
        ("invoices", SupplierInvoice),
        ("matches", ThreeWayMatch),
    ]:
        values = []
        for row in data["finance"][attr]:
            row = dict(row)
            if "roles" in row:
                row["roles"] = RoleAssignment(**row["roles"])
            if attr == "matches":
                row["status"] = MatchStatus(row["status"])
                row["reasons"] = tuple(row["reasons"])
            values.append(cls(**row))
        setattr(engine.controls, attr, values)
    engine.approvals.requests = {
        row["approval_id"]: ApprovalRequest(
            **{**row, "status": ApprovalStatus(row["status"])}
        )
        for row in data["approvals"]
    }
    engine.approvals._counter = len(engine.approvals.requests)
    engine._pending = {
        k: Proposal.model_validate(v) for k, v in data["pending"].items()
    }
    engine._outcomes = {k: ProposalOutcome(**v) for k, v in data["outcomes"].items()}
    for key, value in data["clock"].items():
        setattr(engine.clock, key, value)
    engine.paused = data.get("paused", True)
    engine.speed = data.get("speed", 1)
    engine.faults = data.get("faults", {})


def command(method):
    """Refresh shared state, execute, and commit all economic records + events."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock, self.bus.defer_notifications(), self.bus.store.atomic():
            nested = self._command_depth > 0
            if not nested:
                self.refresh()
                before = export_state(self)
            self._command_depth += 1
            try:
                result = method(self, *args, **kwargs)
                if not nested:
                    self._version = self.bus.store.save_state(
                        self.session_id, export_state(self)
                    )
                return result
            except BaseException:
                if not nested:
                    restore_state(self, before)
                raise
            finally:
                self._command_depth -= 1

    return wrapped
