"""Timeboxed SpacetimeDB adapter seam.

This module intentionally does not invent a Python SDK or reducer API. The
official client docs currently make TypeScript support clear, while this
environment has no verified Python writer credentials. The runtime therefore
keeps SQLite as the default and fails closed if ``AGENTROPOLIS_STORE=spacetime`` is
requested without an explicitly verified adapter.
"""

from __future__ import annotations

from pathlib import Path

from .schemas import EventEnvelope


class SpacetimeUnavailable(RuntimeError):
    pass


class SpacetimeStore:
    """Interface-compatible placeholder that never masquerades as live."""

    mode = "spacetime-unverified"

    def __init__(self, uri: str | None = None, database: str | None = None) -> None:
        self.uri = uri
        self.database = database
        raise SpacetimeUnavailable(
            "SpacetimeDB spike not verified: configure a supported Python client and reducer contract before AGENTROPOLIS_STORE=spacetime"
        )

    def append(self, event: EventEnvelope) -> EventEnvelope:
        raise SpacetimeUnavailable("SpacetimeDB writer is not verified")

    def get_by_idempotency(self, key: str):
        raise SpacetimeUnavailable("SpacetimeDB reader is not verified")

    def since(self, seq: int = 0):
        raise SpacetimeUnavailable("SpacetimeDB reader is not verified")

    def all(self):
        raise SpacetimeUnavailable("SpacetimeDB reader is not verified")
