from app.economy.engine import Business, EconomyEngine
from app.events.schemas import Proposal, ProposalType
from app.finance.approvals import ApprovalManager
from app.economy.inventory import Inventory


def make_engine() -> EconomyEngine:
    engine = EconomyEngine(approvals=ApprovalManager(threshold_cents=50_000, minimum_reserve_cents=20_000))
    engine.register_business(Business("buyer", "Buyer", "shop", "buyer", .99, 20_000, 200_000), 100_000)
    engine.register_business(Business("seller", "Seller", "supplier", "supplier", .9, 10_000, 200_000, inventory=Inventory({"beans":100}),catalog={"beans":{"unit":"unit","cost_price_cents":500}}), 100_000)
    return engine


def make_proposal(**overrides):
    values = dict(type=ProposalType.OFFER, proposal_id="p1", idempotency_key="same", agent_id="procurement", business_id="buyer", counterparty_id="seller", item="beans", quantity=2, unit_price_cents=1000, total_cents=2000, public_rationale="best reliability-adjusted price")
    values.update(overrides)
    return Proposal(**values)


def test_payment_is_idempotent_even_when_replayed_100_times():
    engine = make_engine()
    outcomes = [engine.submit_proposal(make_proposal()) for _ in range(100)]
    assert all(outcome.status == "executed" for outcome in outcomes)
    assert len(engine.bank.transactions) == 0
    engine.deliver_contract(outcomes[0].deal_id)
    for _ in range(100): engine.pay_contract(outcomes[0].deal_id)
    assert len(engine.bank.transactions) == 1
    assert engine.ledger.is_balanced()


def test_reserve_violation_is_structured_and_does_not_mutate():
    engine = make_engine()
    result = engine.submit_proposal(make_proposal(idempotency_key="reserve", total_cents=90_001, unit_price_cents=90_001, quantity=1))
    assert result.status == "rejected"
    assert result.validation["reason_code"] == "RESERVE_VIOLATION"
    assert len(engine.contracts) == 0


def test_high_value_offer_requires_approval_then_posts():
    engine = make_engine()
    result = engine.submit_proposal(make_proposal(idempotency_key="approval", total_cents=60_000, unit_price_cents=60_000, quantity=1))
    assert result.status == "approval_required"
    assert engine.approvals.pending()
    final = engine.resolve_approval(result.approval_id or "", "human_operator", True)
    assert final.status == "executed"
    assert engine.ledger.is_balanced()


def test_stale_deal_offer_is_rejected():
    engine = make_engine()
    first = engine.submit_proposal(make_proposal(idempotency_key="first", deal_id="deal-fixed"))
    assert first.status == "executed"
    stale = engine.submit_proposal(make_proposal(idempotency_key="stale", deal_id="deal-fixed"))
    assert stale.status == "rejected"
    assert stale.validation["reason_code"] == "STALE_OFFER"

