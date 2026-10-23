from app.economy.engine import EconomyEngine
from app.economy.scenarios import inject
from app.api.economy import EconomyRuntime


def test_supplier_bankruptcy_replans_to_reliable_supplier():
    runtime = EconomyRuntime()
    result = inject(runtime.engine, "supplier_bankruptcy")
    assert result["ok"] is True
    assert result["replacement_supplier"] == "wildflower_supply"
    assert any(contract.contract_id.startswith("recovery_") for contract in runtime.engine.contracts.values())
    assert any(event.type == "SupplierDefaulted" for event in runtime.engine.bus.replay())
    assert runtime.engine.ledger.is_balanced()

