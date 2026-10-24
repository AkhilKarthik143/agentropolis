from dataclasses import replace

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import economy as api


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(
        api, "settings", replace(api.settings, data_dir=tmp_path, store="memory")
    )
    monkeypatch.setattr(api, "_simulations", {})
    monkeypatch.setattr(api, "_runtime", None)
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(api.simulation_router)

    @app.websocket("/ws/{simulation_id}")
    async def stream(websocket: WebSocket, simulation_id: str, since: int = 0):
        await api.simulation_ws(websocket, simulation_id, since)

    with TestClient(app) as test_client:
        yield test_client
    for runtime in api._simulations.values():
        runtime.agent_runtime.store.close()


def create(client, name="guards", store="memory"):
    response = client.post(
        "/api/simulations", json={"simulation_id": name, "store": store}
    )
    assert response.status_code == 200, response.text
    return f"/api/simulations/{name}"


def test_requests_reject_coerced_money_inventory_and_policy(client):
    path = create(client)
    for field in (
        "cash_cents",
        "budget_cents",
        "reserve_cents",
        "spend_limit_cents",
        "low_stock_threshold",
    ):
        for value in (True, 5.0, "5"):
            response = client.post(
                f"{path}/businesses", json={"name": "Invalid", field: value}
            )
            assert response.status_code == 422, (field, value, response.text)
    for value in (True, 5.0, "5", -1):
        assert (
            client.post(
                f"{path}/businesses",
                json={"name": "Invalid", "inventory": {"coffee_beans": value}},
            ).status_code
            == 422
        )
    for field in (
        "reserve_cents",
        "spend_limit_cents",
        "demand_per_tick",
        "low_stock_threshold",
    ):
        assert (
            client.patch(
                f"{path}/businesses/cafe_lumen", json={field: True}
            ).status_code
            == 422
        )
    for value in (True, 5.0, "5"):
        assert (
            client.post(
                f"{path}/contracts/deal_beans_001/deliver", json={"quantity": value}
            ).status_code
            == 422
        )
    assert (
        api.get_simulation("guards")
        .engine.contracts["deal_beans_001"]
        .delivered_quantity
        == 0
    )


def test_update_role_validation_preserves_existing_team(client):
    path = create(client)
    runtime = api.get_simulation("guards")
    before = set(runtime.agent_runtime.registry.agents)
    response = client.patch(
        f"{path}/businesses/cafe_lumen",
        json={"agent_roles": ["fabricated_payment_admin"]},
    )
    assert response.status_code == 422
    assert set(runtime.agent_runtime.registry.agents) == before
    assert runtime.engine.businesses["cafe_lumen"].agent_roles == []


def test_partial_receipt_and_empty_body_completion(client):
    path = create(client)
    partial = client.post(
        f"{path}/contracts/deal_beans_001/deliver", json={"quantity": 5}
    )
    assert partial.status_code == 200
    assert partial.json()["fulfillment_state"] == "PARTIALLY_RECEIVED"
    assert partial.json()["received_quantity"] == 5
    assert client.post(f"{path}/contracts/deal_beans_001/pay").status_code == 409
    complete = client.post(f"{path}/contracts/deal_beans_001/deliver")
    assert complete.status_code == 200
    assert complete.json()["received_quantity"] == 24
    assert client.post(f"{path}/contracts/missing/deliver").status_code == 409


def test_legacy_partial_receipt_uses_the_created_default_session(client):
    create(client, "demo_001")
    partial = client.post(
        "/api/economy/contracts/deal_beans_001/deliver", json={"quantity": 3}
    )
    assert partial.status_code == 200
    assert partial.json()["received_quantity"] == 3
    assert api.get_runtime() is api._simulations["demo_001"]
    assert client.post("/api/economy/contracts/missing/deliver").status_code == 409


def test_sessions_isolate_mutations_events_and_durable_reload(client):
    left = create(client, "left", "sqlite")
    right = create(client, "right", "sqlite")
    response = client.post(f"{left}/businesses", json={"name": "Only Left"})
    assert response.status_code == 200
    assert "biz_only_left" not in api.get_simulation("right").engine.businesses
    client.post(f"{left}/contracts/deal_beans_001/deliver", json={"quantity": 4})
    assert (
        api.get_simulation("right")
        .engine.contracts["deal_beans_001"]
        .delivered_quantity
        == 0
    )
    left_events = client.get(f"{left}/events").json()
    right_events = client.get(f"{right}/events").json()
    assert {event["session_id"] for event in left_events} == {"left"}
    assert {event["session_id"] for event in right_events} == {"right"}
    retired = api._simulations.pop("left")
    retired.agent_runtime.store.close()
    assert (
        client.post("/api/simulations", json={"simulation_id": "left"}).status_code
        == 409
    )
    assert client.get(left).status_code == 200
    restored = api.get_simulation("left")
    assert "biz_only_left" in restored.engine.businesses
    assert restored.engine.contracts["deal_beans_001"].delivered_quantity == 4


def test_reset_notifies_old_websocket_and_reconnect_uses_new_bus(client):
    path = create(client)
    runtime = api.get_simulation("guards")
    last_seq = runtime.engine.bus.replay()[-1].seq
    with client.websocket_connect(f"/ws/guards?since={last_seq}") as socket:
        assert client.post(f"{path}/reset").status_code == 200
        # ClockPaused can already be queued before the reset signal is set.
        for _ in range(5):
            event = socket.receive_json()
            if event["type"] == "resync":
                break
        assert event["payload"] == {"since": 0, "reason": "simulation_reset"}
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1012
    replacement = api.get_simulation("guards")
    assert replacement is not runtime
    with client.websocket_connect(
        f"/ws/guards?since={replacement.engine.bus.replay()[-1].seq}"
    ) as socket:
        assert (
            client.post(f"{path}/businesses", json={"name": "After Reset"}).status_code
            == 200
        )
        assert socket.receive_json()["type"] == "BusinessRegistered"


def test_scheduler_respects_independent_speeds_pause_and_speed_change(monkeypatch):
    class Engine:
        def __init__(self, speed):
            self.speed, self.paused, self.ticks = speed, False, 0

        def refresh(self):
            pass

        def tick(self):
            self.ticks += 1

    class Runtime:
        def __init__(self, speed):
            self.engine = Engine(speed)

    slow, fast = Runtime(1), Runtime(4)
    monkeypatch.setattr(api, "_simulations", {"slow": slow, "fast": fast})
    schedules = {}
    for step in range(9):
        api._advance_schedules(step / 4, schedules)
    assert slow.engine.ticks == 2
    assert fast.engine.ticks == 5
    fast.engine.paused = True
    slow.engine.speed = 2
    api._advance_schedules(2.25, schedules)
    api._advance_schedules(3.25, schedules)
    assert slow.engine.ticks == 3
    assert fast.engine.ticks == 5
