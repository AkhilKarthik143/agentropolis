import json
import os

from app.api.economy import EconomyRuntime


def test_seed_replay_is_deterministic(monkeypatch):
    monkeypatch.setenv("AGENTROPOLIS_STORE", "memory")
    first = EconomyRuntime()
    second = EconomyRuntime()
    first_log = [event.model_dump(mode="json") for event in first.engine.bus.replay()]
    second_log = [event.model_dump(mode="json") for event in second.engine.bus.replay()]
    assert json.dumps(first_log, sort_keys=True) == json.dumps(second_log, sort_keys=True)
    assert first.engine.ledger.trial_balance() == second.engine.ledger.trial_balance()

