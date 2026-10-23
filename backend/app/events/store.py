from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Iterable, Protocol

from .audit import GENESIS_HASH, hash_event, with_integrity
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
        self._lock = Lock()

    def append(self, event: EventEnvelope) -> EventEnvelope:
        with self._lock:
            seq = len(self.events) + 1
            previous = self.events[-1].hash if self.events else GENESIS_HASH
            stored = with_integrity(event, seq=seq, prev_hash=previous or GENESIS_HASH)
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


class SqliteStore:
    """Small offline-durable store; all writes are serialized in one transaction."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        apply_migrations(self.path)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS economy_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    session_id TEXT,
                    business_id TEXT,
                    deal_id TEXT,
                    correlation_id TEXT,
                    causation_id TEXT,
                    idempotency_key TEXT UNIQUE,
                    payload TEXT NOT NULL,
                    prev_hash TEXT,
                    hash TEXT
                )"""
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(economy_events)")}
            if "session_id" not in columns:
                conn.execute("ALTER TABLE economy_events ADD COLUMN session_id TEXT")
            if "prev_hash" not in columns:
                conn.execute("ALTER TABLE economy_events ADD COLUMN prev_hash TEXT")
            if "hash" not in columns:
                conn.execute("ALTER TABLE economy_events ADD COLUMN hash TEXT")
            self._backfill_integrity(conn)

    def _backfill_integrity(self, conn: sqlite3.Connection) -> None:
        """One-time migration for Stage 1 rows created before hash chaining."""

        rows = conn.execute(
            "SELECT seq, ts, type, session_id, business_id, deal_id, correlation_id, causation_id, idempotency_key, payload, prev_hash, hash FROM economy_events ORDER BY seq"
        ).fetchall()
        previous = GENESIS_HASH
        for row in rows:
            event = self._row(row)
            if event.prev_hash and event.hash:
                previous = event.hash
                continue
            prepared = with_integrity(event, seq=event.seq, prev_hash=previous)
            conn.execute("UPDATE economy_events SET prev_hash = ?, hash = ? WHERE seq = ?", (prepared.prev_hash, prepared.hash, prepared.seq))
            previous = prepared.hash or previous

    @staticmethod
    def _row(row: tuple) -> EventEnvelope:
        return EventEnvelope(
            seq=row[0], ts=row[1], type=row[2], session_id=row[3], business_id=row[4], deal_id=row[5],
            correlation_id=row[6], causation_id=row[7], idempotency_key=row[8],
            payload=json.loads(row[9]), prev_hash=row[10], hash=row[11],
        )

    def append(self, event: EventEnvelope) -> EventEnvelope:
        with self._lock, sqlite3.connect(self.path) as conn:
            previous_row = conn.execute("SELECT hash FROM economy_events ORDER BY seq DESC LIMIT 1").fetchone()
            previous = (previous_row[0] if previous_row and previous_row[0] else GENESIS_HASH)
            seq = int(conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM economy_events").fetchone()[0])
            stored = with_integrity(event, seq=seq, prev_hash=previous)
            cursor = conn.execute(
                """INSERT INTO economy_events
                (ts, type, session_id, business_id, deal_id, correlation_id, causation_id, idempotency_key, payload, prev_hash, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (stored.ts.isoformat(), stored.type, stored.session_id, stored.business_id, stored.deal_id,
                 stored.correlation_id, stored.causation_id, stored.idempotency_key,
                 json.dumps(stored.payload, sort_keys=True), stored.prev_hash, stored.hash),
            )
            seq = cursor.lastrowid
        return stored.model_copy(update={"seq": int(seq)})

    def get_by_idempotency(self, key: str) -> EventEnvelope | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT seq, ts, type, session_id, business_id, deal_id, correlation_id, causation_id, idempotency_key, payload, prev_hash, hash FROM economy_events WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        return self._row(row) if row else None

    def since(self, seq: int = 0) -> list[EventEnvelope]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT seq, ts, type, session_id, business_id, deal_id, correlation_id, causation_id, idempotency_key, payload, prev_hash, hash FROM economy_events WHERE seq > ? ORDER BY seq",
                (seq,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def all(self) -> list[EventEnvelope]:
        return self.since(0)

