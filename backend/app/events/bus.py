from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from threading import RLock, local
from contextlib import contextmanager

from .schemas import EventEnvelope
from .store import EventStore, MemoryStore


class EventBus:
    """Append-only event log with replay and bounded per-subscriber fan-out."""

    def __init__(self, store: EventStore | None = None, max_queue: int = 256) -> None:
        self.store = store or MemoryStore()
        self.max_queue = max_queue
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()
        self._lock = RLock()
        self._local = local()

    def append(self, event: EventEnvelope) -> EventEnvelope:
        with self._lock:
            if event.idempotency_key:
                duplicate = self.store.get_by_idempotency(event.idempotency_key)
                if duplicate:
                    return duplicate
            stored = self.store.append(event)
            subscribers = tuple(self._subscribers)
        pending = getattr(self._local, "pending", None)
        if pending is not None:
            pending.append((stored, subscribers))
            return stored
        self._publish(stored, subscribers)
        return stored

    @contextmanager
    def defer_notifications(self):
        if getattr(self._local, "pending", None) is not None:
            yield
            return
        self._local.pending = []
        try:
            yield
            pending = self._local.pending
        except BaseException:
            self._local.pending = None
            raise
        self._local.pending = None
        for event, subscribers in pending:
            self._publish(event, subscribers)

    def _publish(self, stored, subscribers):
        for queue in subscribers:
            try:
                queue.put_nowait(stored)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(
                        EventEnvelope(
                            type="resync",
                            seq=stored.seq,
                            payload={"since": max(0, stored.seq - self.max_queue)},
                        )
                    )
                except asyncio.QueueFull:
                    pass
        return stored

    def replay(self, since: int = 0) -> list[EventEnvelope]:
        return self.store.since(since)

    async def subscribe(self, since: int = 0) -> AsyncIterator[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=self.max_queue)
        # Snapshot and register atomically.  Otherwise an append between the
        # backfill query and subscriber registration can disappear on reconnect.
        with self._lock:
            backlog = self.store.since(since)
            if len(backlog) > self.max_queue:
                latest = backlog[-1]
                queue.put_nowait(
                    EventEnvelope(
                        type="resync",
                        seq=latest.seq,
                        session_id=latest.session_id,
                        payload={"since": max(0, latest.seq - self.max_queue)},
                    )
                )
                backlog = backlog[-(self.max_queue - 1) :] if self.max_queue > 1 else []
            for event in backlog:
                queue.put_nowait(event)
            self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
