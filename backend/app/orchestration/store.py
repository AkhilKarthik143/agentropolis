"""SQLite queue, leases, task state and private agent memory.

Delivery is at least once. Acknowledgements are transport receipts, never proof
of economic success; command idempotency remains the engine's responsibility.
All keys include the simulation. BEGIN IMMEDIATE serializes claims across worker
processes, while expiring leases let another worker recover interrupted work.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4

from app.events.schemas import AgentMessage, AgentTask


class RuntimeStore:
    def __init__(self, simulation_id: str, path: str | Path | None = None) -> None:
        self.simulation_id = simulation_id
        self.path = str(path) if path is not None else ":memory:"
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=30000")
        if path is not None:
            self.connection.execute("PRAGMA journal_mode=WAL")
        migration = Path(__file__).resolve().parents[2] / "migrations" / "003_agent_runtime.sql"
        self.connection.executescript(migration.read_text())
        self.connection.commit()
        self._lock = RLock()
        self.worker_id = uuid4().hex

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise

    def close(self) -> None:
        self.connection.close()

    def enqueue(self, message: AgentMessage, *, tick: int, ttl: int = 12) -> bool:
        if message.simulation_id != self.simulation_id:
            raise PermissionError("message belongs to another simulation")
        if ttl <= 0:
            raise ValueError("message ttl must be positive")
        with self.transaction() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO agent_runtime_messages "
                "(simulation_id,message_id,idempotency_key,payload,available_tick,expires_tick) VALUES(?,?,?,?,?,?)",
                (self.simulation_id, message.message_id, message.idempotency_key, message.model_dump_json(), tick, tick + ttl),
            )
            return cursor.rowcount == 1

    def expire(self, tick: int) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            rows = conn.execute("SELECT * FROM agent_runtime_messages WHERE simulation_id=? AND status IN ('queued','retry','processing') AND expires_tick<?", (self.simulation_id, tick)).fetchall()
            conn.execute("UPDATE agent_runtime_messages SET status='expired', lease_until=NULL,lease_owner=NULL WHERE simulation_id=? AND status IN ('queued','retry','processing') AND expires_tick<?", (self.simulation_id, tick))
            return [self._message(row) for row in rows]

    def claim(self, tick: int, *, now: float | None = None, lease_seconds: float = 30) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        with self.transaction() as conn:
            conn.execute("UPDATE agent_runtime_messages SET status='retry',lease_until=NULL,lease_owner=NULL WHERE simulation_id=? AND status='processing' AND lease_until<=?", (self.simulation_id, now))
            row = conn.execute("SELECT * FROM agent_runtime_messages WHERE simulation_id=? AND status IN ('queued','retry') AND available_tick<=? AND expires_tick>=? ORDER BY rowid LIMIT 1", (self.simulation_id, tick, tick)).fetchone()
            if row is None:
                return None
            conn.execute("UPDATE agent_runtime_messages SET status='processing',attempts=attempts+1,lease_until=?,lease_owner=? WHERE simulation_id=? AND message_id=?", (now + lease_seconds, self.worker_id, self.simulation_id, row["message_id"]))
            value = self._message(row)
            value.update(attempts=row["attempts"] + 1, status="processing", lease_owner=self.worker_id)
            return value

    def acknowledge(self, message_id: str) -> None:
        with self.transaction() as conn:
            cursor = conn.execute("UPDATE agent_runtime_messages SET status='acknowledged',acknowledged_at=?,lease_until=NULL,lease_owner=NULL,last_error=NULL WHERE simulation_id=? AND message_id=? AND status='processing' AND lease_owner=?", (datetime.now(timezone.utc).isoformat(), self.simulation_id, message_id, self.worker_id))
            if cursor.rowcount != 1:
                raise RuntimeError("message lease was lost before acknowledgement")

    def fail(self, message_id: str, *, tick: int, error: str, max_attempts: int = 3) -> str:
        with self.transaction() as conn:
            row = conn.execute("SELECT attempts FROM agent_runtime_messages WHERE simulation_id=? AND message_id=? AND lease_owner=?", (self.simulation_id, message_id, self.worker_id)).fetchone()
            if row is None:
                raise RuntimeError("message lease was lost before failure reporting")
            status = "dead_letter" if row["attempts"] >= max_attempts else "retry"
            conn.execute("UPDATE agent_runtime_messages SET status=?,available_tick=?,lease_until=NULL,lease_owner=NULL,last_error=? WHERE simulation_id=? AND message_id=?", (status, tick + min(2 ** (row["attempts"] - 1), 8), error[:500], self.simulation_id, message_id))
            return status

    @staticmethod
    def _message(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["message"] = json.loads(result.pop("payload"))
        return result

    def messages(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._message(row) for row in self.connection.execute("SELECT * FROM agent_runtime_messages WHERE simulation_id=? ORDER BY rowid", (self.simulation_id,))]

    def save_agent(self, payload: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute("INSERT INTO agent_runtime_agents VALUES(?,?,?) ON CONFLICT(simulation_id,agent_id) DO UPDATE SET payload=excluded.payload", (self.simulation_id, payload["agent_id"], json.dumps(payload)))

    def agent(self, agent_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute("SELECT payload FROM agent_runtime_agents WHERE simulation_id=? AND agent_id=?", (self.simulation_id, agent_id)).fetchone()
            return json.loads(row[0]) if row else None

    def save_task(self, task: AgentTask | dict[str, Any]) -> None:
        payload = task.model_dump(mode="json") if isinstance(task, AgentTask) else task
        with self.transaction() as conn:
            conn.execute("INSERT INTO agent_runtime_tasks VALUES(?,?,?,?,?,?) ON CONFLICT(simulation_id,task_id) DO UPDATE SET status=excluded.status,payload=excluded.payload", (self.simulation_id, payload["task_id"], payload.get("correlation_id"), payload["assigned_agent_id"], payload["status"], json.dumps(payload)))

    def tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [json.loads(row[0]) for row in self.connection.execute("SELECT payload FROM agent_runtime_tasks WHERE simulation_id=? ORDER BY rowid", (self.simulation_id,))]

    def update_task(self, task_id: str, status: str, result: dict[str, Any] | None = None) -> None:
        task = next((item for item in self.tasks() if item["task_id"] == task_id), None)
        if task:
            task.update(status=status)
            if result is not None:
                task["result"] = result
            self.save_task(task)

    def save_negotiation(self, payload: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute("INSERT INTO agent_runtime_negotiations VALUES(?,?,?,?,?) ON CONFLICT(simulation_id,negotiation_id) DO UPDATE SET status=excluded.status,payload=excluded.payload", (self.simulation_id, payload["negotiation_id"], payload["business_id"], payload["status"], json.dumps(payload)))

    def negotiations(self, business_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute("SELECT payload FROM agent_runtime_negotiations WHERE simulation_id=? ORDER BY rowid", (self.simulation_id,)).fetchall()
        values = [json.loads(row[0]) for row in rows]
        return [value for value in values if business_id is None or value["business_id"] == business_id]

    def negotiation(self, negotiation_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute("SELECT payload FROM agent_runtime_negotiations WHERE simulation_id=? AND negotiation_id=?", (self.simulation_id, negotiation_id)).fetchone()
        return json.loads(row[0]) if row else None

    def remember(self, agent_id: str, key: str, value: Any) -> None:
        with self.transaction() as conn:
            conn.execute("INSERT INTO agent_runtime_memory VALUES(?,?,?,?) ON CONFLICT(simulation_id,agent_id,memory_key) DO UPDATE SET payload=excluded.payload", (self.simulation_id, agent_id, key, json.dumps(value)))

    def recall(self, agent_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self.connection.execute("SELECT payload FROM agent_runtime_memory WHERE simulation_id=? AND agent_id=? AND memory_key=?", (self.simulation_id, agent_id, key)).fetchone()
        return json.loads(row[0]) if row else default
