from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.economy import (  # noqa: E402
    economy_ws,
    router as economy_router,
    simulation_router,
    simulation_ws,
    start_runtime,
    stop_runtime,
)
from app.core.config import settings  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    await start_runtime()
    try:
        yield
    finally:
        await stop_runtime()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(economy_router)
app.include_router(simulation_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "agentropolis", "status": "ok", "docs": "/docs"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "agentropolis", "status": "ok"}


@app.websocket("/ws/economy")
async def economy_websocket(websocket: WebSocket, since: int = 0) -> None:
    await economy_ws(websocket, since=since)


@app.websocket("/ws/simulations/{simulation_id}")
async def simulation_websocket(websocket: WebSocket, simulation_id: str, since: int = 0) -> None:
    await simulation_ws(websocket, simulation_id, since=since)
