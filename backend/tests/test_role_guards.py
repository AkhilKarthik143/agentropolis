"""Custom teams cannot silently regain omitted operational authority."""

import json

from app.api.economy import EconomyRuntime


def test_recovery_without_manager_records_blocked_outcome_once():
    runtime = EconomyRuntime(store_mode="memory")
    engine = runtime.engine
    engine.update_business("cafe_lumen", {"agent_roles": ["recovery"]})
    engine.shock("supplier_bankruptcy", "northstar_roasters")

    engine.tick()
    engine.tick()

    failures = [
        event
        for event in engine.bus.replay()
        if event.type == "RecoveryFailed" and event.business_id == "cafe_lumen"
    ]
    assert len(failures) == 1
    assert failures[0].payload["status"] == "blocked"
    assert failures[0].payload["reason"] == "manager_agent_unavailable"
    assert failures[0].payload["alternatives"]
    assert not runtime.agent_runtime.store.negotiations("cafe_lumen")
    recovery_messages = [
        row
        for row in runtime.agent_runtime.store.messages()
        if row["message"]["sender_id"] == "recovery_agent:cafe_lumen"
    ]
    assert recovery_messages == []


def test_omitting_payments_role_keeps_received_invoice_unpaid():
    runtime = EconomyRuntime(store_mode="memory")
    engine = runtime.engine
    engine.update_business("cafe_lumen", {"agent_roles": ["accounting"]})
    engine.deliver_contract("deal_beans_001")

    engine.tick()

    assert engine.contracts["deal_beans_001"].payment_state == "APPROVED"
    assert runtime.agent_runtime.registry.by_role("cafe_lumen", "payments") is None


def test_omitting_accounting_role_defers_reconciliation_until_enabled():
    runtime = EconomyRuntime(store_mode="memory")
    engine = runtime.engine
    engine.update_business("cafe_lumen", {"agent_roles": ["payments"]})
    engine.deliver_contract("deal_beans_001")

    engine.tick()

    contract = engine.contracts["deal_beans_001"]
    assert contract.payment_state == "CONFIRMED"
    assert runtime.agent_runtime.registry.by_role("cafe_lumen", "accounting") is None
    engine.update_business("cafe_lumen", {"agent_roles": ["payments", "accounting"]})
    engine.tick()
    assert engine.contracts["deal_beans_001"].payment_state == "RECONCILED"


def test_public_summary_excludes_nested_private_rationale():
    runtime = EconomyRuntime(store_mode="memory")
    runtime.engine.tick()
    store = runtime.agent_runtime.store
    negotiation = store.negotiations()[0]
    negotiation["review"] = {
        "decisions": [
            {
                "private_rationale": "private negotiation notes",
                "reason": "within policy",
            }
        ]
    }
    store.save_negotiation(negotiation)

    assert "private negotiation notes" in json.dumps(store.negotiations())
    public = json.dumps(runtime.engine.summary()["agent_runtime"])
    assert "private_rationale" not in public
    assert "private negotiation notes" not in public
    assert "within policy" in public


def test_nested_private_rationale_is_not_written_to_public_event_stream():
    import json
    from app.api.economy import EconomyRuntime

    runtime = EconomyRuntime(store_mode="memory")
    runtime.engine.tick()
    events = [event.model_dump(mode="json") for event in runtime.engine.bus.replay()]
    assert any(event["type"] == "AgentMessageSent" for event in events)
    assert "private_rationale" not in json.dumps(events)
