"""Integrity helpers for the append-only economy event stream."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .schemas import EventEnvelope

GENESIS_HASH = "0" * 64


def canonical_event(event: EventEnvelope, *, seq: int | None = None, prev_hash: str | None = None) -> str:
    """Return the stable JSON representation used by the event hash chain."""

    data: dict[str, Any] = {
        "seq": event.seq if seq is None else seq,
        "ts": event.ts.isoformat(),
        "type": event.type,
        "session_id": event.session_id,
        "business_id": event.business_id,
        "deal_id": event.deal_id,
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "idempotency_key": event.idempotency_key,
        "payload": event.payload,
        "prev_hash": event.prev_hash if prev_hash is None else prev_hash,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def hash_event(event: EventEnvelope, *, seq: int | None = None, prev_hash: str | None = None) -> str:
    return hashlib.sha256(canonical_event(event, seq=seq, prev_hash=prev_hash).encode("utf-8")).hexdigest()


def with_integrity(event: EventEnvelope, *, seq: int, prev_hash: str) -> EventEnvelope:
    prepared = event.model_copy(update={"seq": seq, "prev_hash": prev_hash, "hash": None})
    return prepared.model_copy(update={"hash": hash_event(prepared)})


def verify_chain(events: Iterable[EventEnvelope]) -> dict[str, Any]:
    """Verify sequence, previous-hash links, and each event's content hash."""

    expected_seq = 1
    previous = GENESIS_HASH
    for event in events:
        if event.seq != expected_seq:
            return {"valid": False, "first_break_seq": event.seq, "reason": "sequence_gap", "expected_seq": expected_seq}
        if event.prev_hash != previous:
            return {"valid": False, "first_break_seq": event.seq, "reason": "prev_hash_mismatch", "expected": previous, "actual": event.prev_hash}
        expected_hash = hash_event(event)
        if event.hash != expected_hash:
            return {"valid": False, "first_break_seq": event.seq, "reason": "hash_mismatch", "expected": expected_hash, "actual": event.hash}
        previous = event.hash
        expected_seq += 1
    return {"valid": True, "first_break_seq": None, "event_count": expected_seq - 1, "last_hash": previous}
