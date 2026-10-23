from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.economy.engine import Business, EconomyEngine
from app.economy.inventory import Inventory
from app.economy.scenarios import SUPPORTED_SHOCKS, inject
from app.events.bus import EventBus
from app.events.schemas import Proposal, ProposalType
from app.events.store import MemoryStore, SqliteStore
from app.finance.approvals import ApprovalError
from app.core.config import settings
from app.orchestration.runtime import AgentRuntime


class EconomyRuntime:
    def __init__(self, *, session_id: str = "demo_001", store_mode: str | None = None) -> None:
        store_mode = (store_mode or os.getenv("AGENTROPOLIS_STORE", settings.store)).lower()
        if store_mode == "spacetime":
            from app.events.spacetime import SpacetimeStore
            store = SpacetimeStore(os.getenv("SPACETIMEDB_URI"), os.getenv("SPACETIMEDB_DATABASE"))
        else:
            store = MemoryStore() if store_mode == "memory" else SqliteStore(settings.event_database)
        self.session_id = session_id
        self.status = "created"
        self.engine = EconomyEngine(bus=EventBus(store=store), seed=int(os.getenv("AGENTROPOLIS_SEED", str(settings.seed))), session_id=session_id)
        self.seed_source = "backend/scenarios/seed_economy.json"
        self.seeded = False
        self.start()

    def start(self) -> None:
        if self.seeded:
            return
        seed_path = Path(__file__).resolve().parents[2] / "scenarios" / "seed_economy.json"
        data = json.loads(seed_path.read_text())
        for row in data["businesses"]:
            self.engine.register_business(Business(
                business_id=row["business_id"], name=row["name"], kind=row["kind"], role=row["role"],
                reliability=float(row["reliability"]), reserve_cents=int(row["reserve_cents"]),
                spend_limit_cents=int(row["spend_limit_cents"]), categories=list(row.get("categories", [])),
                inventory=Inventory(dict(row.get("inventory", {}))),
                objective=str(row.get("objective", "maintain reserve and source reliable suppliers")),
                inventory_item=str(row.get("inventory_item", "coffee_beans")),
                low_stock_threshold=int(row.get("low_stock_threshold", 8)),
                negotiation_style=str(row.get("negotiation_style", "steady")),
                credit_status=str(row.get("credit_status", "passed")),
                credit_score=int(row.get("credit_score", 82)),
                credit_reason=str(row.get("credit_reason", "seeded demo credit result")),
                supplier_note=str(row.get("supplier_note", "")),
                capacity={str(key): int(value) for key, value in row.get("capacity", {}).items()},
            ), opening_cents=int(row["opening_cents"]))
        buyer = self.engine.businesses["cafe_lumen"]
        supplier = self.engine.businesses["northstar_roasters"]
        self.engine.submit_proposal(Proposal(
            type=ProposalType.OFFER, proposal_id="seed_offer_beans", idempotency_key="seed:beans",
            agent_id="procurement_agent", business_id=buyer.business_id, counterparty_id=supplier.business_id,
            deal_id="deal_beans_001", item="coffee_beans", quantity=24, unit="bags", unit_price_cents=4083,
            delivery_days=2, total_cents=97992, payment_terms="on delivery",
            public_rationale="Northstar is the best reliability-adjusted price for this week’s beans.",
            private_rationale="Scored price, delivery, and reliability against the reserve policy.",
        ))
        # The seeded order is already paid, but most of the stock is consumed
        # before the demo starts so the sim-clock scheduler has a real low-stock
        # condition to react to.
        buyer.inventory.consume("coffee_beans", 28)
        self.engine._emit("DemandTick", buyer.business_id, payload={"item": "coffee_beans", "quantity": 28, "reason": "seeded demo demand"}, idempotency_key="seed:demand")
        equipment = next((business for business in self.engine.businesses.values() if business.role == "supplier" and "equipment" in business.categories), supplier)
        self.engine.submit_proposal(Proposal(
            type=ProposalType.OFFER, proposal_id="seed_offer_equipment", idempotency_key="seed:equipment",
            agent_id="procurement_agent", business_id=buyer.business_id, counterparty_id=equipment.business_id,
            deal_id="deal_equipment_001", item="espresso_machine", quantity=1, unit="unit", unit_price_cents=240000,
            delivery_days=5, total_cents=240000, payment_terms="net 7",
            public_rationale="Oakline meets the equipment spec, but this purchase needs human approval.",
            private_rationale="Threshold policy blocks autonomous capital equipment spend.",
        ))
        self.seeded = True
        self.agent_runtime = AgentRuntime(self.engine)
        self.engine.attach_agent_runtime(self.agent_runtime)


_runtime: EconomyRuntime | None = None
_simulations: dict[str, EconomyRuntime] = {}


def get_runtime() -> EconomyRuntime:
    global _runtime
    if _runtime is None:
        _runtime = EconomyRuntime(session_id="demo_001")
        _simulations["demo_001"] = _runtime
    return _runtime


def get_simulation(simulation_id: str) -> EconomyRuntime:
    if simulation_id == "demo_001":
        return get_runtime()
    runtime = _simulations.get(simulation_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="simulation not found")
    return runtime


async def start_runtime() -> EconomyRuntime:
    runtime = get_runtime()
    runtime.status = "ready"
    return runtime


async def stop_runtime() -> None:
    return None


router = APIRouter(prefix="/api/economy", tags=["Agentropolis economy"])


class BusinessCreate(BaseModel):
    name: str
    kind: str = "business"
    role: str = "buyer"
    budget_cents: int = Field(default=1000000, ge=0)
    reserve_cents: int = Field(default=200000, ge=0)
    objective: str = "maintain reserve and source reliable suppliers"


class ApprovalDecision(BaseModel):
    approved: bool
    approver: str = "human_operator"


class ShockRequest(BaseModel):
    shock_type: str | None = None
    type: str | None = None
    supplier_id: str | None = None

    @property
    def requested_type(self) -> str:
        return self.shock_type or self.type or ""


class SimulationCreate(BaseModel):
    simulation_id: str | None = None
    name: str = "Agentropolis demo"
    store: str = "sqlite"


def _simulation_payload(runtime: EconomyRuntime) -> dict[str, Any]:
    return {"simulation_id": runtime.session_id, "status": runtime.status, **runtime.engine.summary()}


@router.get("/summary")
async def summary() -> dict[str, Any]:
    return get_runtime().engine.summary()


@router.get("/businesses")
async def businesses() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return [engine.business_snapshot(business_id) for business_id in engine.businesses]


@router.post("/businesses")
async def create_business(request: BusinessCreate) -> dict[str, Any]:
    runtime = get_runtime()
    engine = runtime.engine
    business_id = "biz_" + "".join(char.lower() if char.isalnum() else "_" for char in request.name).strip("_")
    if business_id in engine.businesses:
        raise HTTPException(status_code=409, detail="business already exists")
    business = engine.register_business(Business(
        business_id=business_id, name=request.name, kind=request.kind, role=request.role,
        reliability=0.9, reserve_cents=request.reserve_cents, spend_limit_cents=request.budget_cents,
        categories=[], objective=request.objective,
    ), opening_cents=request.budget_cents)
    if runtime.agent_runtime:
        runtime.agent_runtime.register_business(business)
    return {"business": engine.business_snapshot(business.business_id), "objective": request.objective}


@router.get("/negotiations")
async def negotiations() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return [engine.contract_snapshot(contract_id) for contract_id in engine.contracts]


@router.get("/approvals")
async def approvals() -> list[dict[str, Any]]:
    return get_runtime().engine.approvals.snapshot()


@router.post("/approvals/{approval_id}")
async def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict[str, Any]:
    try:
        outcome = get_runtime().engine.resolve_approval(approval_id, decision.approver, decision.approved)
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return outcome.as_dict()


@router.get("/ledger")
async def ledger(business_id: str | None = None) -> dict[str, Any]:
    engine = get_runtime().engine
    return {"entries": engine.ledger.snapshot(business_id), "trial_balance": engine.ledger.trial_balance(business_id)}


@router.get("/transactions")
async def transactions() -> list[dict[str, Any]]:
    return [transaction.__dict__ for transaction in get_runtime().engine.bank.history()]


@router.get("/decisions")
async def decisions() -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in get_runtime().engine.bus.replay() if "validation" in event.payload or event.type in {"ApprovalRequested", "ApprovalGranted", "ApprovalDenied"}]


@router.get("/agents")
async def agents() -> dict[str, Any]:
    runtime = get_runtime()
    return runtime.agent_runtime.snapshot() if runtime.agent_runtime else {"agents": [], "tasks": [], "messages": []}


@router.get("/agents/tasks")
async def agent_tasks() -> list[dict[str, Any]]:
    runtime = get_runtime()
    return runtime.agent_runtime.snapshot()["tasks"] if runtime.agent_runtime else []


@router.get("/agents/messages")
async def agent_messages() -> list[dict[str, Any]]:
    runtime = get_runtime()
    return runtime.agent_runtime.snapshot()["messages"] if runtime.agent_runtime else []


@router.post("/tick")
async def tick() -> dict[str, Any]:
    engine = get_runtime().engine
    return {"clock": engine.clock.now(), "actions": engine.tick()}


@router.post("/contracts/{deal_id}/deliver")
async def deliver_contract(deal_id: str) -> dict[str, Any]:
    try:
        return get_runtime().engine.deliver_contract(deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/events")
async def events(since: int = Query(default=0, ge=0)) -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in get_runtime().engine.bus.replay(since)]


@router.get("/audit/verify")
async def verify_audit() -> dict[str, Any]:
    return get_runtime().engine.audit_verification()


@router.get("/ledger/proof")
async def ledger_proof(business_id: str | None = None) -> dict[str, Any]:
    return get_runtime().engine.ledger_proof(business_id)


@router.get("/audit/{deal_id}")
async def audit(deal_id: str) -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in get_runtime().engine.bus.replay() if event.deal_id == deal_id]


@router.get("/scenarios")
async def scenarios() -> dict[str, Any]:
    return {"supported": list(SUPPORTED_SHOCKS), "clock": get_runtime().engine.clock.now()}


@router.post("/scenarios/shock")
async def shock(request: ShockRequest) -> dict[str, Any]:
    try:
        return inject(get_runtime().engine, request.requested_type, supplier_id=request.supplier_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/replay")
async def replay() -> dict[str, Any]:
    engine = get_runtime().engine
    events = engine.bus.replay()
    return {"mode": "deterministic event replay", "event_count": len(events), "last_seq": events[-1].seq if events else 0, "seed": os.getenv("AGENTROPOLIS_SEED", str(settings.seed))}


@router.websocket("/ws")
async def economy_ws(websocket: WebSocket, since: int = 0) -> None:
    await websocket.accept()
    stream = get_runtime().engine.bus.subscribe(since)
    try:
        while True:
            try:
                event = await asyncio.wait_for(stream.__anext__(), timeout=15)
                await websocket.send_json(event.model_dump(mode="json"))
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except (WebSocketDisconnect, StopAsyncIteration, asyncio.CancelledError):
        return
    finally:
        await stream.aclose()


# Session-shaped API used by the revised Agentropolis contract.  The original
# /api/economy routes remain as a compatibility surface for the first UI build.
simulation_router = APIRouter(prefix="/api/simulations", tags=["Agentropolis simulations"])


@simulation_router.post("")
async def create_simulation(request: SimulationCreate) -> dict[str, Any]:
    simulation_id = request.simulation_id or f"sim_{uuid4().hex[:8]}"
    if simulation_id in _simulations:
        raise HTTPException(status_code=409, detail="simulation already exists")
    runtime = EconomyRuntime(session_id=simulation_id, store_mode=request.store)
    _simulations[simulation_id] = runtime
    return _simulation_payload(runtime)


@simulation_router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    runtime.status = "running"
    runtime.engine._emit("SimulationStarted", payload={"simulation_id": simulation_id})
    runtime.engine.tick()
    return _simulation_payload(runtime)


@simulation_router.get("/suppliers")
async def simulation_suppliers() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return [engine.business_snapshot(business.business_id) for business in engine.businesses.values() if business.role == "supplier"]


@simulation_router.get("/{simulation_id}")
async def simulation(simulation_id: str) -> dict[str, Any]:
    return _simulation_payload(get_simulation(simulation_id))


@simulation_router.get("/{simulation_id}/events")
async def simulation_events(simulation_id: str, since: int = Query(default=0, ge=0)) -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in get_simulation(simulation_id).engine.bus.replay(since)]


@simulation_router.get("/{simulation_id}/audit/verify")
async def simulation_audit_verify(simulation_id: str) -> dict[str, Any]:
    return get_simulation(simulation_id).engine.audit_verification()


@simulation_router.get("/{simulation_id}/ledger/proof")
async def simulation_ledger_proof(simulation_id: str, business_id: str | None = None) -> dict[str, Any]:
    return get_simulation(simulation_id).engine.ledger_proof(business_id)


@simulation_router.post("/{simulation_id}/shock")
async def simulation_shock(simulation_id: str, request: ShockRequest) -> dict[str, Any]:
    try:
        return inject(get_simulation(simulation_id).engine, request.requested_type, supplier_id=request.supplier_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@simulation_router.post("/{simulation_id}/approvals/{approval_id}")
async def simulation_approval(simulation_id: str, approval_id: str, decision: ApprovalDecision) -> dict[str, Any]:
    try:
        return get_simulation(simulation_id).engine.resolve_approval(approval_id, decision.approver, decision.approved).as_dict()
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@simulation_router.post("/{simulation_id}/contracts/{deal_id}/deliver")
async def simulation_deliver_contract(simulation_id: str, deal_id: str) -> dict[str, Any]:
    try:
        return get_simulation(simulation_id).engine.deliver_contract(deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@simulation_router.get("/{simulation_id}/agents")
async def simulation_agents(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    return runtime.agent_runtime.snapshot() if runtime.agent_runtime else {"agents": [], "tasks": [], "messages": []}


@simulation_router.post("/{simulation_id}/replay")
async def simulation_replay(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    events = runtime.engine.bus.replay()
    return {"simulation_id": simulation_id, "mode": "deterministic event replay", "event_count": len(events), "last_seq": events[-1].seq if events else 0, "seed": os.getenv("AGENTROPOLIS_SEED", str(settings.seed))}


async def simulation_ws(websocket: WebSocket, simulation_id: str, since: int = 0) -> None:
    runtime = get_simulation(simulation_id)
    await websocket.accept()
    stream = runtime.engine.bus.subscribe(since)
    try:
        while True:
            try:
                event = await asyncio.wait_for(stream.__anext__(), timeout=15)
                await websocket.send_json(event.model_dump(mode="json"))
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except (WebSocketDisconnect, StopAsyncIteration, asyncio.CancelledError):
        return
    finally:
        await stream.aclose()

