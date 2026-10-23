from app.api.economy import EconomyRuntime


def test_agent_teams_run_typed_procurement_and_defer_delivery():
    runtime = EconomyRuntime(store_mode="memory")
    engine = runtime.engine
    buyer = engine.businesses["cafe_lumen"]
    before = buyer.inventory.quantity("coffee_beans")

    actions = engine.tick()

    assert actions and actions[0]["status"] == "executed"
    assert len(runtime.agent_runtime.registry.for_business("cafe_lumen")) == 7
    assert len(runtime.agent_runtime.registry.for_businesses_by_role("supplier")) == 4
    assert any(event.type == "AgentTaskAssigned" for event in engine.bus.replay())
    assert any(event.type == "AgentMessageSent" for event in engine.bus.replay())
    contract = engine.contracts[actions[0]["deal_id"]]
    assert contract.delivery_mode == "on_receipt"
    assert contract.state.value == "AWAITING_DELIVERY"
    assert buyer.inventory.quantity("coffee_beans") == before

    delivered = engine.deliver_contract(contract.contract_id)
    assert delivered["delivered_quantity"] == contract.quantity
    assert buyer.inventory.quantity("coffee_beans") == before + contract.quantity
    assert delivered["state"] == "DELIVERED"


def test_agent_risk_excludes_blocked_and_low_reliability_suppliers():
    runtime = EconomyRuntime(store_mode="memory")
    runtime.engine.tick()
    events = runtime.engine.bus.replay()
    blocked = [event for event in events if event.type == "CRS_CHECKED" and event.payload.get("supplier_id") == "supplier_shady"]
    low_reliability = [event for event in events if event.type == "CRS_CHECKED" and event.payload.get("supplier_id") == "daybreak_packaging"]
    assert blocked
    assert low_reliability
    assert not any(event.type == "OfferReceived" and event.payload.get("quote", {}).get("supplier_id") == "supplier_shady" for event in events)
