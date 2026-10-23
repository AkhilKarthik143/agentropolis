from app.economy.scoring import score_offer
from app.finance.controls import FinanceControlError, FinanceControls, PurchaseOrder, RoleAssignment, SupplierInvoice
from app.finance.ledger import Ledger
from app.finance.treasury import TreasuryService
from app.integrations.apify import ApifySupplierIntel


def test_offer_score_is_transparent_and_bounded():
    result = score_offer({"price_cents": 3_700, "delivery_days": 2, "reliability": 0.82}, owner_preferences={"required_reliability": 0.7})
    assert 0 <= result["score"] <= 100
    assert set(result["factors"]) == {"price", "delivery", "reliability", "owner_preference"}
    assert round(sum(item["contribution"] for item in result["factors"].values()) * 100, 2) == result["score"]


def test_treasury_service_parks_exceptional_spend():
    ledger = Ledger()
    ledger.seed_cash("buyer", 100_000)
    decision = TreasuryService().evaluate(ledger, "buyer", 50_000, 20_000, spend_limit_cents=80_000, approval_threshold_cents=50_000)
    assert decision.decision == "NEEDS_HUMAN"


def test_duplicate_supplier_invoice_number_is_blocked():
    controls = FinanceControls()
    roles = RoleAssignment("requester", "approver", "payer", "poster")
    controls.create_po(PurchaseOrder("po1", "buyer", "seller", "beans", 1, 100, 100, "on delivery", "OPS", roles))
    first = SupplierInvoice("inv1", "INV-1", "po1", "seller", 100, "2026-01-08", "on delivery", 0, "OPS")
    controls.record_invoice(first)
    try:
        controls.record_invoice(SupplierInvoice("inv2", "INV-1", "po1", "seller", 100, "2026-01-08", "on delivery", 0, "OPS"))
    except FinanceControlError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate invoice number was accepted")


def test_apify_fixture_has_provenance_and_normalization():
    fixture = ApifySupplierIntel(mode="fixture").market_reference()
    assert fixture.mode == "fixture"
    normalized = ApifySupplierIntel.normalize_dataset_row({"price": 41.5, "url": "fixture://market"})
    assert normalized.median_price_cents == 4_150
    assert normalized.provenance == "fixture://market"
