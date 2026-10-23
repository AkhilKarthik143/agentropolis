from app.economy.engine import Business, EconomyEngine
from app.finance.reconciliation import reconcile_business


def test_reconciliation_surfaces_bank_mismatch():
    engine = EconomyEngine()
    engine.register_business(Business("buyer", "Buyer", "shop", "buyer", .9, 10, 1000), 1000)
    account = engine.businesses["buyer"].account_id
    engine.bank.accounts[account] += 1
    result = reconcile_business("buyer", account, engine.ledger, engine.bank)
    assert result.ok is False
    assert result.mismatch_cents == 1

