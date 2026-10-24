from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
import re

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
    def __init__(self, *, session_id="demo_001", store_mode=None):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            raise ValueError(
                "simulation id must use letters, digits, underscore or hyphen"
            )
        store_mode = (
            store_mode or os.getenv("AGENTROPOLIS_STORE", settings.store)
        ).lower()
        if store_mode not in {"memory", "sqlite"}:
            raise ValueError("durable economic execution supports sqlite or memory")
        store = (
            MemoryStore()
            if store_mode == "memory"
            else SqliteStore(settings.data_dir / "sessions" / f"{session_id}.db")
        )
        self.session_id = session_id
        self.status = "ready"
        self.reset_event = asyncio.Event()
        self.store_mode = store_mode
        self.engine = EconomyEngine(
            bus=EventBus(store=store), seed=settings.seed, session_id=session_id
        )
        self.seed_source = "backend/scenarios/seed_economy.json"
        self.start()

    def start(self):
        if not self.engine.seeded:
            data = json.loads(
                (
                    Path(__file__).resolve().parents[2]
                    / "scenarios"
                    / "seed_economy.json"
                ).read_text()
            )
            for row in data["businesses"]:
                row = dict(row)
                opening = row.pop("opening_cents")
                row["inventory"] = Inventory(row.get("inventory", {}))
                self.engine.register_business(Business(**row), opening)
            # A disclosed initial contract supplies the disruption demo. It has
            # reserved stock only: no fabricated receipt, invoice, or payment.
            self.engine.submit_proposal(
                Proposal(
                    type=ProposalType.OFFER,
                    proposal_id="seed_offer_beans",
                    idempotency_key="seed:beans",
                    agent_id="seed_service",
                    business_id="cafe_lumen",
                    counterparty_id="northstar_roasters",
                    deal_id="deal_beans_001",
                    item="coffee_beans",
                    quantity=24,
                    unit="bags",
                    unit_price_cents=4083,
                    total_cents=97992,
                    delivery_days=3,
                    payment_terms="on receipt",
                    public_rationale="Seed contract for the repeatable supply-crisis scenario.",
                )
            )
            self.engine.submit_proposal(
                Proposal(
                    type=ProposalType.OFFER,
                    proposal_id="seed_offer_equipment",
                    idempotency_key="seed:equipment",
                    agent_id="seed_service",
                    business_id="cafe_lumen",
                    counterparty_id="oakline_equipment",
                    deal_id="deal_equipment_001",
                    item="espresso_machine",
                    quantity=1,
                    unit="unit",
                    unit_price_cents=240000,
                    total_cents=240000,
                    delivery_days=5,
                    public_rationale="Equipment capital purchase requires human approval.",
                )
            )
            self.engine.seeded = True
            self.engine.checkpoint()
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
        if (
            re.fullmatch(r"[A-Za-z0-9_-]{1,64}", simulation_id)
            and (settings.data_dir / "sessions" / f"{simulation_id}.db").exists()
        ):
            runtime = EconomyRuntime(session_id=simulation_id, store_mode="sqlite")
            _simulations[simulation_id] = runtime
        else:
            raise HTTPException(status_code=404, detail="simulation not found")
    return runtime


_scheduler_task = None


def _advance_schedules(now: float, schedules: dict) -> float:
    """Advance each running simulation on its own monotonic deadline."""
    runtimes = set(_simulations.values())
    for old in set(schedules) - runtimes:
        schedules.pop(old, None)
    next_delay = 0.25
    for runtime in runtimes:
        engine = runtime.engine
        engine.refresh()
        if engine.paused:
            schedules.pop(runtime, None)
            continue
        period = 2 / engine.speed
        previous = schedules.get(runtime)
        deadline = now if previous is None else previous[1]
        if previous is not None and previous[0] != engine.speed:
            deadline = now + period
        if now >= deadline:
            try:
                engine.tick()
            except Exception as exc:
                engine.set_clock(paused=True)
                engine._emit(
                    "SchedulerFailed", payload={"error_type": type(exc).__name__}
                )
                schedules.pop(runtime, None)
                continue
            deadline = now + period
        schedules[runtime] = (engine.speed, deadline)
        next_delay = min(next_delay, max(0.01, deadline - now))
    return next_delay


async def _scheduler():
    schedules = {}
    loop = asyncio.get_running_loop()
    while True:
        await asyncio.sleep(_advance_schedules(loop.time(), schedules))


async def start_runtime():
    global _scheduler_task
    runtime = get_runtime()
    _scheduler_task = asyncio.create_task(_scheduler())
    return runtime


async def stop_runtime():
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


router = APIRouter(prefix="/api/economy", tags=["Agentropolis economy"])

NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
VALID_AGENT_ROLES = {
    "manager",
    "inventory",
    "procurement",
    "negotiation",
    "treasury",
    "risk",
    "payments",
    "supplier",
    "accounting",
    "accounts_payable",
    "accounts_receivable",
    "controller",
    "broker",
    "recovery",
    "strategy",
    "market_intelligence",
    "credit",
    "auditor",
}


def _validate_agent_roles(roles: list[str] | None) -> None:
    if roles is not None and set(roles) - VALID_AGENT_ROLES:
        raise HTTPException(422, "unknown agent roles")


class BusinessCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    kind: str = "retail"
    role: Literal["buyer", "supplier", "broker"] = "buyer"
    cash_cents: int = Field(default=1000000, ge=0, le=1000000000, strict=True)
    budget_cents: int | None = Field(default=None, ge=0, strict=True)
    reserve_cents: int = Field(default=200000, ge=0, strict=True)
    spend_limit_cents: int = Field(default=500000, ge=0, strict=True)
    objective: str = Field(
        default="maintain reserve and source reliable suppliers", max_length=1000
    )
    inventory_item: str = "coffee_beans"
    low_stock_threshold: int = Field(default=8, ge=0, le=10000, strict=True)
    categories: list[str] = Field(default_factory=list)
    inventory: dict[str, NonnegativeInt] = Field(default_factory=dict)
    catalog: dict[str, dict] = Field(default_factory=dict)
    agent_roles: list[str] = Field(default_factory=list)


class BusinessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str | None = Field(default=None, max_length=1000)
    reserve_cents: int | None = Field(default=None, ge=0, strict=True)
    spend_limit_cents: int | None = Field(default=None, ge=0, strict=True)
    active: bool | None = None
    agent_roles: list[str] | None = None
    required_reliability: float | None = Field(default=None, ge=0, le=1)
    demand_per_tick: int | None = Field(default=None, ge=0, le=10000, strict=True)
    low_stock_threshold: int | None = Field(default=None, ge=0, le=10000, strict=True)


class SpeedRequest(BaseModel):
    speed: float = Field(ge=0.25, le=4, strict=True)


class ReceiptRequest(BaseModel):
    quantity: int | None = Field(default=None, gt=0, strict=True)


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
    return {
        "simulation_id": runtime.session_id,
        "status": runtime.status,
        **runtime.engine.summary(),
    }


@router.get("/summary")
async def summary() -> dict[str, Any]:
    return get_runtime().engine.summary()


@router.get("/businesses")
async def businesses() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return [engine.business_snapshot(business_id) for business_id in engine.businesses]


def _create_business(runtime, request):
    engine = runtime.engine
    _validate_agent_roles(request.agent_roles)
    for product in request.catalog.values():
        if any(
            type(product.get(key, 0)) is not int or product.get(key, 0) < 0
            for key in ("unit_price_cents", "cost_price_cents", "lead_days")
        ):
            raise HTTPException(422, "invalid catalog amounts")
    business_id = "biz_" + "".join(
        char.lower() if char.isalnum() else "_" for char in request.name
    ).strip("_")
    if business_id in engine.businesses:
        raise HTTPException(409, "business already exists")
    if not business_id.strip("biz_"):
        raise HTTPException(422, "name must include letters or numbers")
    if any(type(value) is not int or value < 0 for value in request.inventory.values()):
        raise HTTPException(422, "inventory quantities must be nonnegative integers")
    cash = (
        request.budget_cents if request.budget_cents is not None else request.cash_cents
    )
    business = engine.register_business(
        Business(
            business_id,
            request.name,
            request.kind,
            request.role,
            0.9,
            request.reserve_cents,
            request.spend_limit_cents,
            categories=request.categories,
            inventory=Inventory(request.inventory),
            objective=request.objective,
            inventory_item=request.inventory_item,
            low_stock_threshold=request.low_stock_threshold,
            catalog=request.catalog,
            agent_roles=request.agent_roles,
        ),
        cash,
    )
    runtime.agent_runtime.register_business(business)
    return {
        "business": engine.business_snapshot(business_id),
        "objective": request.objective,
    }


@router.post("/businesses")
async def create_business(request: BusinessCreate):
    return _create_business(get_runtime(), request)


@router.get("/negotiations")
async def negotiations() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return get_runtime().agent_runtime.snapshot().get("negotiations", [])


@router.get("/approvals")
async def approvals() -> list[dict[str, Any]]:
    return get_runtime().engine.approvals.snapshot()


@router.post("/approvals/{approval_id}")
async def decide_approval(
    approval_id: str, decision: ApprovalDecision
) -> dict[str, Any]:
    try:
        outcome = get_runtime().engine.resolve_approval(
            approval_id, decision.approver, decision.approved
        )
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return outcome.as_dict()


@router.get("/ledger")
async def ledger(business_id: str | None = None) -> dict[str, Any]:
    engine = get_runtime().engine
    return {
        "entries": engine.ledger.snapshot(business_id),
        "trial_balance": engine.ledger.trial_balance(business_id),
    }


@router.get("/transactions")
async def transactions() -> list[dict[str, Any]]:
    return [transaction.__dict__ for transaction in get_runtime().engine.bank.history()]


@router.get("/decisions")
async def decisions() -> list[dict[str, Any]]:
    return [
        event.model_dump(mode="json")
        for event in get_runtime().engine.bus.replay()
        if "validation" in event.payload
        or event.type in {"ApprovalRequested", "ApprovalGranted", "ApprovalDenied"}
    ]


@router.get("/agents")
async def agents() -> dict[str, Any]:
    runtime = get_runtime()
    return (
        runtime.agent_runtime.snapshot()
        if runtime.agent_runtime
        else {"agents": [], "tasks": [], "messages": []}
    )


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
    actions = engine.tick()
    return {"clock": engine.clock.now(), "actions": actions}


@router.post("/contracts/{deal_id}/deliver")
async def deliver_contract(
    deal_id: str, request: ReceiptRequest | None = None
) -> dict[str, Any]:
    try:
        return get_runtime().engine.deliver_contract(
            deal_id, quantity=request.quantity if request else None
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/events")
async def events(since: int = Query(default=0, ge=0)) -> list[dict[str, Any]]:
    return [
        event.model_dump(mode="json")
        for event in get_runtime().engine.bus.replay(since)
    ]


@router.get("/audit/verify")
async def verify_audit() -> dict[str, Any]:
    return get_runtime().engine.audit_verification()


@router.get("/ledger/proof")
async def ledger_proof(business_id: str | None = None) -> dict[str, Any]:
    return get_runtime().engine.ledger_proof(business_id)


@router.get("/audit/{deal_id}")
async def audit(deal_id: str) -> list[dict[str, Any]]:
    return [
        event.model_dump(mode="json")
        for event in get_runtime().engine.bus.replay()
        if event.deal_id == deal_id
    ]


@router.get("/scenarios")
async def scenarios() -> dict[str, Any]:
    return {
        "supported": list(SUPPORTED_SHOCKS),
        "clock": get_runtime().engine.clock.now(),
    }


@router.post("/scenarios/shock")
async def shock(request: ShockRequest) -> dict[str, Any]:
    try:
        return inject(
            get_runtime().engine,
            request.requested_type,
            supplier_id=request.supplier_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/replay")
async def replay() -> dict[str, Any]:
    engine = get_runtime().engine
    events = engine.bus.replay()
    return {
        "mode": "deterministic event replay",
        "event_count": len(events),
        "last_seq": events[-1].seq if events else 0,
        "seed": os.getenv("AGENTROPOLIS_SEED", str(settings.seed)),
    }


@router.websocket("/ws")
async def economy_ws(websocket: WebSocket, since: int = 0) -> None:
    await _stream_runtime(websocket, get_runtime(), since)


async def _stream_runtime(
    websocket: WebSocket, runtime: EconomyRuntime, since: int
) -> None:
    await websocket.accept()
    stream = runtime.engine.bus.subscribe(since)
    next_event = asyncio.create_task(stream.__anext__())
    reset = asyncio.create_task(runtime.reset_event.wait())
    try:
        while True:
            done, _ = await asyncio.wait(
                {next_event, reset}, timeout=15, return_when=asyncio.FIRST_COMPLETED
            )
            if reset in done:
                # Reset restarts event sequence numbers. Refresh from zero and
                # reconnect against the replacement bus, not the retired one.
                await websocket.send_json(
                    {
                        "type": "resync",
                        "payload": {"since": 0, "reason": "simulation_reset"},
                    }
                )
                await websocket.close(code=1012, reason="simulation reset")
                return
            if next_event in done:
                event = next_event.result()
                next_event = asyncio.create_task(stream.__anext__())
                await websocket.send_json(event.model_dump(mode="json"))
            else:
                await websocket.send_json({"type": "heartbeat"})
    except (WebSocketDisconnect, StopAsyncIteration, asyncio.CancelledError):
        return
    finally:
        next_event.cancel()
        reset.cancel()
        try:
            await next_event
        except (asyncio.CancelledError, StopAsyncIteration):
            pass
        try:
            await reset
        except asyncio.CancelledError:
            pass
        await stream.aclose()


# Session-shaped API used by the revised Agentropolis contract.  The original
# /api/economy routes remain as a compatibility surface for the first UI build.
simulation_router = APIRouter(
    prefix="/api/simulations", tags=["Agentropolis simulations"]
)


@simulation_router.post("")
async def create_simulation(request: SimulationCreate) -> dict[str, Any]:
    global _runtime
    simulation_id = request.simulation_id or f"sim_{uuid4().hex[:8]}"
    persisted = (
        re.fullmatch(r"[A-Za-z0-9_-]{1,64}", simulation_id)
        and (settings.data_dir / "sessions" / f"{simulation_id}.db").exists()
    )
    if simulation_id in _simulations or persisted:
        raise HTTPException(status_code=409, detail="simulation already exists")
    try:
        runtime = EconomyRuntime(session_id=simulation_id, store_mode=request.store)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _simulations[simulation_id] = runtime
    if simulation_id == "demo_001":
        _runtime = runtime
    return _simulation_payload(runtime)


@simulation_router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    runtime.status = "running"
    runtime.engine.set_clock(paused=False)
    runtime.engine._emit("SimulationStarted", payload={"simulation_id": simulation_id})
    runtime.engine.tick()
    return _simulation_payload(runtime)


@simulation_router.get("/suppliers")
async def simulation_suppliers() -> list[dict[str, Any]]:
    engine = get_runtime().engine
    return [
        engine.business_snapshot(business.business_id)
        for business in engine.businesses.values()
        if business.role == "supplier"
    ]


@simulation_router.get("/{simulation_id}")
async def simulation(simulation_id: str) -> dict[str, Any]:
    return _simulation_payload(get_simulation(simulation_id))


@simulation_router.get("/{simulation_id}/events")
async def simulation_events(
    simulation_id: str, since: int = Query(default=0, ge=0)
) -> list[dict[str, Any]]:
    return [
        event.model_dump(mode="json")
        for event in get_simulation(simulation_id).engine.bus.replay(since)
    ]


@simulation_router.get("/{simulation_id}/audit/verify")
async def simulation_audit_verify(simulation_id: str) -> dict[str, Any]:
    return get_simulation(simulation_id).engine.audit_verification()


@simulation_router.get("/{simulation_id}/ledger/proof")
async def simulation_ledger_proof(
    simulation_id: str, business_id: str | None = None
) -> dict[str, Any]:
    return get_simulation(simulation_id).engine.ledger_proof(business_id)


@simulation_router.post("/{simulation_id}/shock")
async def simulation_shock(simulation_id: str, request: ShockRequest) -> dict[str, Any]:
    try:
        return inject(
            get_simulation(simulation_id).engine,
            request.requested_type,
            supplier_id=request.supplier_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@simulation_router.post("/{simulation_id}/approvals/{approval_id}")
async def simulation_approval(
    simulation_id: str, approval_id: str, decision: ApprovalDecision
) -> dict[str, Any]:
    try:
        return (
            get_simulation(simulation_id)
            .engine.resolve_approval(approval_id, decision.approver, decision.approved)
            .as_dict()
        )
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@simulation_router.post("/{simulation_id}/contracts/{deal_id}/deliver")
async def simulation_deliver_contract(
    simulation_id: str, deal_id: str, request: ReceiptRequest | None = None
) -> dict[str, Any]:
    try:
        return get_simulation(simulation_id).engine.deliver_contract(
            deal_id, quantity=request.quantity if request else None
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@simulation_router.get("/{simulation_id}/agents")
async def simulation_agents(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    return (
        runtime.agent_runtime.snapshot()
        if runtime.agent_runtime
        else {"agents": [], "tasks": [], "messages": []}
    )


@simulation_router.post("/{simulation_id}/replay")
async def simulation_replay(simulation_id: str) -> dict[str, Any]:
    runtime = get_simulation(simulation_id)
    events = runtime.engine.bus.replay()
    return {
        "simulation_id": simulation_id,
        "mode": "deterministic event replay",
        "event_count": len(events),
        "last_seq": events[-1].seq if events else 0,
        "seed": os.getenv("AGENTROPOLIS_SEED", str(settings.seed)),
    }


async def simulation_ws(
    websocket: WebSocket, simulation_id: str, since: int = 0
) -> None:
    await _stream_runtime(websocket, get_simulation(simulation_id), since)


@simulation_router.post("/{simulation_id}/businesses")
async def session_create_business(simulation_id: str, request: BusinessCreate):
    return _create_business(get_simulation(simulation_id), request)


@simulation_router.patch("/{simulation_id}/businesses/{business_id}")
async def session_update_business(
    simulation_id: str, business_id: str, request: BusinessUpdate
):
    runtime = get_simulation(simulation_id)
    _validate_agent_roles(request.agent_roles)
    try:
        business = runtime.engine.update_business(
            business_id, request.model_dump(exclude_none=True)
        )
    except KeyError:
        raise HTTPException(404, "business not found")
    runtime.agent_runtime.register_business(runtime.engine.businesses[business_id])
    return {"business": business}


@simulation_router.post("/{simulation_id}/tick")
async def session_tick(simulation_id: str):
    engine = get_simulation(simulation_id).engine
    actions = engine.tick()
    return {"clock": engine.clock.now(), "actions": actions}


@simulation_router.post("/{simulation_id}/pause")
async def session_pause(simulation_id: str):
    return get_simulation(simulation_id).engine.set_clock(paused=True)


@simulation_router.post("/{simulation_id}/resume")
async def session_resume(simulation_id: str):
    return get_simulation(simulation_id).engine.set_clock(paused=False)


@simulation_router.post("/{simulation_id}/speed")
async def session_speed(simulation_id: str, request: SpeedRequest):
    return get_simulation(simulation_id).engine.set_clock(speed=request.speed)


@simulation_router.post("/{simulation_id}/contracts/{deal_id}/ship")
async def session_ship(simulation_id: str, deal_id: str):
    try:
        return get_simulation(simulation_id).engine.ship_contract(deal_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@simulation_router.post("/{simulation_id}/contracts/{deal_id}/pay")
async def session_pay(simulation_id: str, deal_id: str):
    try:
        return get_simulation(simulation_id).engine.pay_contract(deal_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@simulation_router.post("/{simulation_id}/payments/{payment_id}/reconcile")
async def session_reconcile(simulation_id: str, payment_id: str):
    try:
        return get_simulation(simulation_id).engine.reconcile_payment(payment_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@simulation_router.post("/{simulation_id}/reset")
async def session_reset(simulation_id: str):
    global _runtime
    runtime = get_simulation(simulation_id)
    runtime.engine.set_clock(paused=True)
    if runtime.engine.bank.mode != "mock":
        raise HTTPException(409, "only local simulations can reset")
    store = runtime.engine.bus.store
    if hasattr(runtime.agent_runtime.registry, "store"):
        runtime.agent_runtime.registry.store.close()
    if isinstance(store, SqliteStore):
        # Keep a recoverable complete database checkpoint, including its WAL.
        import sqlite3

        backup = (
            settings.data_dir / "checkpoints" / f"{simulation_id}-{uuid4().hex[:8]}.db"
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(store.path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        with sqlite3.connect(store.path) as conn:
            for table in [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                if row[0] not in {"schema_migrations", "sqlite_sequence"}
            ]:
                conn.execute('DELETE FROM "' + table.replace('"', '""') + '"')
    new = EconomyRuntime(session_id=simulation_id, store_mode=runtime.store_mode)
    _simulations[simulation_id] = new
    if simulation_id == "demo_001":
        _runtime = new
    runtime.reset_event.set()
    return _simulation_payload(new)
