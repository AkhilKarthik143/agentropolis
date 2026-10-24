"""Hash-chained events and atomic economic snapshots.

SQLite BEGIN IMMEDIATE protects sequence assignment and command snapshots across
processes. An engine command writes its events and state in the same transaction.
"""

from __future__ import annotations

import copy
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock, local
from typing import Protocol

from .audit import GENESIS_HASH, with_integrity
from .schemas import EventEnvelope
from app.database.migrations import apply_migrations


class EventStore(Protocol):
    def append(self, event: EventEnvelope) -> EventEnvelope: ...
    def get_by_idempotency(self, key: str) -> EventEnvelope | None: ...
    def since(self, seq: int = 0) -> list[EventEnvelope]: ...
    def all(self) -> list[EventEnvelope]: ...


class MemoryStore:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []
        self._idempotency: dict[str, EventEnvelope] = {}
        self._lock = RLock()
        self.states: dict[str, dict] = {}
        self.revision: dict[str, int] = {}

    @contextmanager
    def atomic(self):
        with self._lock:
            checkpoint = copy.deepcopy(
                (self.events, self._idempotency, self.states, self.revision)
            )
            try:
                yield self
            except BaseException:
                self.events, self._idempotency, self.states, self.revision = checkpoint
                raise

    def append(self, event: EventEnvelope) -> EventEnvelope:
        with self._lock:
            if event.idempotency_key in self._idempotency:
                return self._idempotency[event.idempotency_key]
            stored = with_integrity(
                event,
                seq=len(self.events) + 1,
                prev_hash=(self.events[-1].hash if self.events else GENESIS_HASH)
                or GENESIS_HASH,
            )
            self.events.append(stored)
            if stored.idempotency_key:
                self._idempotency[stored.idempotency_key] = stored
            return stored

    def get_by_idempotency(self, key: str) -> EventEnvelope | None:
        return self._idempotency.get(key)

    def since(self, seq: int = 0) -> list[EventEnvelope]:
        return [event for event in self.events if event.seq > seq]

    def all(self) -> list[EventEnvelope]:
        return list(self.events)

    def load_state(self, session_id: str):
        state = self.states.get(session_id)
        return (
            (self.revision[session_id], copy.deepcopy(state))
            if state is not None
            else None
        )

    def save_state(self, session_id: str, payload: dict) -> int:
        self.revision[session_id] = self.revision.get(session_id, 0) + 1
        self.states[session_id] = copy.deepcopy(payload)
        return self.revision[session_id]


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._local = local()
        apply_migrations(self.path)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(economy_events)")
            }
            for name in ("session_id", "prev_hash", "hash"):
                if name not in columns:
                    conn.execute(f"ALTER TABLE economy_events ADD COLUMN {name} TEXT")
            previous = GENESIS_HASH
            for row in conn.execute(
                "SELECT seq,ts,type,session_id,business_id,deal_id,correlation_id,causation_id,idempotency_key,payload,prev_hash,hash FROM economy_events ORDER BY seq"
            ).fetchall():
                event = self._row(row)
                if not event.hash:
                    event = with_integrity(event, seq=event.seq, prev_hash=previous)
                    conn.execute(
                        "UPDATE economy_events SET prev_hash=?,hash=? WHERE seq=?",
                        (event.prev_hash, event.hash, event.seq),
                    )
                previous = event.hash

    @contextmanager
    def connection(self):
        current = getattr(self._local, "connection", None)
        if current is not None:
            yield current
            return
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @contextmanager
    def atomic(self):
        with self._lock:
            if getattr(self._local, "connection", None) is not None:
                yield self
                return
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._local.connection = conn
                try:
                    yield self
                finally:
                    self._local.connection = None

    @staticmethod
    def _row(row):
        return EventEnvelope(
            seq=row[0],
            ts=row[1],
            type=row[2],
            session_id=row[3],
            business_id=row[4],
            deal_id=row[5],
            correlation_id=row[6],
            causation_id=row[7],
            idempotency_key=row[8],
            payload=json.loads(row[9]),
            prev_hash=row[10],
            hash=row[11],
        )

    def append(self, event: EventEnvelope) -> EventEnvelope:
        with self.atomic(), self.connection() as conn:
            if event.idempotency_key:
                duplicate = self.get_by_idempotency(event.idempotency_key)
                if duplicate:
                    return duplicate
            last = conn.execute(
                "SELECT seq,hash FROM economy_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            stored = with_integrity(
                event,
                seq=last[0] + 1 if last else 1,
                prev_hash=last[1] if last else GENESIS_HASH,
            )
            conn.execute(
                "INSERT INTO economy_events(seq,ts,type,session_id,business_id,deal_id,correlation_id,causation_id,idempotency_key,payload,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    stored.seq,
                    stored.ts.isoformat(),
                    stored.type,
                    stored.session_id,
                    stored.business_id,
                    stored.deal_id,
                    stored.correlation_id,
                    stored.causation_id,
                    stored.idempotency_key,
                    json.dumps(stored.payload, sort_keys=True),
                    stored.prev_hash,
                    stored.hash,
                ),
            )
            return stored

    def get_by_idempotency(self, key: str) -> EventEnvelope | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT seq,ts,type,session_id,business_id,deal_id,correlation_id,causation_id,idempotency_key,payload,prev_hash,hash FROM economy_events WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        return self._row(row) if row else None

    def since(self, seq: int = 0) -> list[EventEnvelope]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT seq,ts,type,session_id,business_id,deal_id,correlation_id,causation_id,idempotency_key,payload,prev_hash,hash FROM economy_events WHERE seq>? ORDER BY seq",
                (seq,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def all(self):
        return self.since()

    def load_state(self, session_id: str):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT version,payload FROM economic_snapshots WHERE session_id=?",
                (session_id,),
            ).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def save_state(self, session_id: str, payload: dict) -> int:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO economic_snapshots(session_id,version,payload) VALUES(?,1,?) ON CONFLICT(session_id) DO UPDATE SET version=version+1,payload=excluded.payload",
                (session_id, json.dumps(payload, sort_keys=True)),
            )
            return conn.execute(
                "SELECT version FROM economic_snapshots WHERE session_id=?",
                (session_id,),
            ).fetchone()[0]
