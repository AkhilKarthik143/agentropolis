from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from app.economy.engine import Business, EconomyEngine
from app.economy.inventory import Inventory
from app.events.bus import EventBus
from app.events.store import SqliteStore, MemoryStore
from app.events.schemas import Proposal
from app.finance.ledger import Account, JournalEntry, Ledger, LedgerLine, LedgerError


def seeded(store=None):
    e = EconomyEngine(bus=EventBus(store or MemoryStore()), session_id="integrity")
    e.register_business(
        Business("buyer", "Buyer", "retail", "buyer", 0.99, 20000, 200000), 100000
    )
    e.register_business(
        Business(
            "seller",
            "Seller",
            "manufacturing",
            "supplier",
            0.9,
            1000,
            200000,
            categories=["widgets"],
            inventory=Inventory({"widgets": 10}),
            catalog={
                "widgets": {
                    "unit": "unit",
                    "unit_price_cents": 1000,
                    "cost_price_cents": 600,
                }
            },
        ),
        10000,
    )
    return e


def offer(key="one", **kw):
    return Proposal(
        **{
            **dict(
                type="OFFER",
                agent_id="procurement_agent:buyer",
                business_id="buyer",
                counterparty_id="seller",
                item="widgets",
                quantity=2,
                unit="unit",
                unit_price_cents=1000,
                total_cents=2000,
                proposal_id=key,
                idempotency_key=key,
            ),
            **kw,
        }
    )


def test_receipt_invoice_payment_and_reconciliation_are_distinct():
    e = seeded()
    cash = e.bank.balance(e.businesses["buyer"].account_id)
    out = e.submit_proposal(offer())
    cid = out.deal_id
    assert out.status == "executed"
    assert e.businesses["seller"].inventory.available("widgets") == 8
    assert e.businesses["buyer"].inventory.quantity("widgets") == 0
    assert (
        e.controls.receipts == []
        and e.controls.invoices == []
        and e.bank.history() == []
    )
    with pytest.raises(ValueError, match="receipt"):
        e.pay_contract(cid)
    e.ship_contract(cid)
    e.deliver_contract(cid)
    assert e.businesses["buyer"].inventory.quantity("widgets") == 2
    assert e.ledger.balance("buyer", Account.ACCOUNTS_PAYABLE) == -2000
    assert e.ledger.balance("seller", Account.ACCOUNTS_RECEIVABLE) == 2000
    assert e.ledger.balance("seller", Account.COGS) == 1200
    assert e.bank.balance(e.businesses["buyer"].account_id) == cash
    p = e.pay_contract(cid)
    assert p["status"] == "CONFIRMED"
    assert e.reconcile_payment(p["payment_id"])["status"] == "RECONCILED"
    assert e.ledger.balance("buyer", Account.ACCOUNTS_PAYABLE) == 0
    assert e.ledger.balance("seller", Account.ACCOUNTS_RECEIVABLE) == 0
    assert all(e.ledger.is_balanced(bid) for bid in e.businesses)
    assert all(r["ok"] for r in e.summary()["reconciliation"])


def test_idempotency_does_not_duplicate_stock_or_settlement():
    e = seeded()
    cid = e.submit_proposal(offer()).deal_id
    for _ in range(100):
        assert e.submit_proposal(offer()).deal_id == cid
    for _ in range(10):
        e.deliver_contract(cid)
        e.pay_contract(cid)
    assert len(e.bank.history()) == 1
    assert e.businesses["buyer"].inventory.quantity("widgets") == 2
    assert e.businesses["seller"].inventory.quantity("widgets") == 8


def test_partial_delivery_cannot_pay_full_invoice():
    e = seeded()
    cid = e.submit_proposal(offer()).deal_id
    e.deliver_contract(cid, quantity=1)
    assert e.contracts[cid].fulfillment_state == "PARTIALLY_RECEIVED"
    assert e.ledger.balance("buyer", Account.ACCOUNTS_PAYABLE) == -1000
    with pytest.raises(ValueError):
        e.pay_contract(cid)
    e.deliver_contract(cid, quantity=1)
    e.pay_contract(cid)
    assert e.ledger.balance("buyer", Account.INVENTORY) == 2000


def test_authority_scope_and_total_cannot_be_forged():
    e = seeded()
    for kw, code in [
        ({"agent_id": "accounting_agent:buyer"}, "ROLE_FORBIDDEN"),
        ({"agent_id": "payments_agent:seller"}, "AGENT_SCOPE"),
        ({"session_id": "foreign"}, "SESSION_MISMATCH"),
        ({"total_cents": 1}, "TOTAL_MISMATCH"),
    ]:
        result = e.submit_proposal(offer(code, **kw))
        assert result.validation["reason_code"] == code
    assert not e.contracts


def test_inventory_overselling_is_blocked():
    e = seeded()
    assert (
        e.submit_proposal(offer("large", quantity=8, total_cents=8000)).status
        == "executed"
    )
    result = e.submit_proposal(offer("extra", quantity=3, total_cents=3000))
    assert result.validation["reason_code"] == "INSUFFICIENT_STOCK"


def test_unpaid_contracts_commit_cash():
    e = seeded()
    assert (
        e.submit_proposal(
            offer("a", quantity=1, unit_price_cents=60000, total_cents=60000)
        ).status
        == "executed"
    )
    out = e.submit_proposal(
        offer("b", quantity=1, unit_price_cents=30000, total_cents=30000)
    )
    assert out.validation["reason_code"] == "RESERVE_VIOLATION"


def test_failed_payment_has_no_cash_entry_and_retry_is_single():
    e = seeded()
    cid = e.submit_proposal(offer()).deal_id
    e.deliver_contract(cid)
    e.faults["payment:buyer"] = True
    e.checkpoint()
    assert e.pay_contract(cid)["status"] == "FAILED"
    assert not e.bank.history()
    assert e.ledger.balance("buyer", Account.CASH) == 100000
    assert e.pay_contract(cid)["status"] == "CONFIRMED"
    assert len(e.bank.history()) == 1


def test_uncertain_payment_never_automatically_resubmits():
    e = seeded()
    cid = e.submit_proposal(offer()).deal_id
    e.deliver_contract(cid)
    e._prepare_payment(cid)
    e._payment_failure(cid, "UNCERTAIN", "timeout")
    assert e.pay_contract(cid)["status"] == "UNCERTAIN"
    assert not e.bank.history()


def test_restart_restores_contract_reservations_ledger_and_idempotency(tmp_path):
    path = tmp_path / "restart.db"
    e = seeded(SqliteStore(path))
    cid = e.submit_proposal(offer()).deal_id
    e.deliver_contract(cid)
    e.pay_contract(cid)
    restored = EconomyEngine(bus=EventBus(SqliteStore(path)), session_id="integrity")
    assert restored.submit_proposal(offer()).deal_id == cid
    assert restored.pay_contract(cid)["status"] == "CONFIRMED"
    assert len(restored.bank.history()) == 1
    assert restored.businesses["seller"].inventory.quantity("widgets") == 8
    assert restored.audit_verification()["valid"]
    assert all(r["ok"] for r in restored.summary()["reconciliation"])


def test_two_workers_cannot_oversell_or_pay_twice(tmp_path):
    path = tmp_path / "concurrent.db"
    e = seeded(SqliteStore(path))
    other = EconomyEngine(bus=EventBus(SqliteStore(path)), session_id="integrity")
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda pair: pair[0].submit_proposal(
                    offer(pair[1], quantity=8, total_cents=8000)
                ),
                [(e, "a"), (other, "b")],
            )
        )
    assert sum(r.status == "executed" for r in results) == 1
    cid = next(r.deal_id for r in results if r.status == "executed")
    e.deliver_contract(cid)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda engine: engine.pay_contract(cid), [e, other]))
    e.refresh()
    assert len(e.bank.history()) == 1
    assert e.audit_verification()["valid"]


def test_cross_entity_balancing_is_rejected():
    with pytest.raises(LedgerError, match="each accounting entity"):
        Ledger().post(
            JournalEntry(
                "bad",
                "buyer",
                (
                    LedgerLine(Account.CASH, 100, "buyer"),
                    LedgerLine(Account.CASH, -100, "seller"),
                ),
            )
        )


def test_failed_command_rolls_back_events_and_state(tmp_path, monkeypatch):
    e = seeded(SqliteStore(tmp_path / "rollback.db"))
    before = len(e.bus.replay())
    original = e._emit

    def failure(kind, *args, **kwargs):
        original(kind, *args, **kwargs)
        if kind == "ContractAccepted":
            raise RuntimeError("injected interruption")

    monkeypatch.setattr(e, "_emit", failure)
    with pytest.raises(RuntimeError):
        e.submit_proposal(offer())
    assert (
        not e.contracts and e.businesses["seller"].inventory.available("widgets") == 10
    )
    assert len(e.bus.replay()) == before


def test_approval_is_bound_to_exact_terms():
    e = seeded()
    e.approvals.threshold_cents = 1000
    result = e.submit_proposal(offer())
    assert result.status == "approval_required"
    e._pending[result.approval_id].quantity = 3
    with pytest.raises(ValueError, match="terms changed"):
        e.resolve_approval(result.approval_id, "human_operator", True)
    assert not e.bank.history()
