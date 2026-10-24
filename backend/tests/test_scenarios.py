from app.api.economy import EconomyRuntime
from app.economy.scenarios import inject


def test_shock_only_injects_condition_and_agents_recover_from_current_offers():
    r = EconomyRuntime(store_mode="memory")
    e = r.engine
    before = len(e.contracts)
    result = inject(e, "supplier_bankruptcy", "northstar_roasters")
    assert result["ok"] and len(e.contracts) == before
    assert not e.businesses["northstar_roasters"].active
    actions = e.tick()
    replacements = [
        c
        for c in e.contracts.values()
        if c.buyer_id == "cafe_lumen" and c.supplier_id != "northstar_roasters"
    ]
    assert len(replacements) == 1
    assert (
        len(r.agent_runtime.store.negotiations("cafe_lumen")[0]["expected_suppliers"])
        >= 2
    )
    assert any(a["status"] == "executed" for a in actions)
    assert replacements[0].delivered_quantity == 0
    for _ in range(4):
        e.tick()
    assert replacements[0].fulfillment_state == "RECEIVED"
    assert replacements[0].payment_state == "RECONCILED"
    assert all(e.ledger.is_balanced(bid) for bid in e.businesses)


def test_no_feasible_supplier_is_a_real_recovery_failure():
    r = EconomyRuntime(store_mode="memory")
    e = r.engine
    for bid in ("wildflower_supply", "daybreak_packaging"):
        e.update_business(bid, {"active": False})
    e.shock("supplier_bankruptcy", "northstar_roasters")
    e.tick()
    assert not any(
        c.buyer_id == "cafe_lumen" and c.supplier_id != "northstar_roasters"
        for c in e.contracts.values()
    )
    assert any(
        v.type in {"RecoveryFailed", "NegotiationRejected"} for v in e.bus.replay()
    )


def test_failure_does_not_default_unrelated_supplier_or_received_goods():
    r = EconomyRuntime(store_mode="memory")
    e = r.engine
    e.deliver_contract("deal_beans_001")
    e.shock("supplier_bankruptcy", "wildflower_supply")
    assert e.businesses["northstar_roasters"].active
    assert e.contracts["deal_beans_001"].fulfillment_state == "RECEIVED"
    assert e.businesses["cafe_lumen"].inventory.quantity("coffee_beans") == 28
