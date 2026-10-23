"""Market-reference adapter with a deterministic offline fixture."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx


@dataclass(frozen=True)
class MarketReference:
    item: str
    unit: str
    median_price_cents: int
    source: str
    mode: str
    provenance: str


class ApifySupplierIntel:
    """Fetch or fixture-normalize one market reference for price anchoring."""

    def __init__(self, mode: str | None = None, token: str | None = None, actor_id: str | None = None) -> None:
        self.mode = (mode or os.getenv("APIFY_MODE", "fixture")).lower()
        self.token = token or os.getenv("APIFY_API_TOKEN")
        self.actor_id = actor_id or os.getenv("APIFY_ACTOR_ID")

    def market_reference(self, item: str = "coffee_beans") -> MarketReference:
        if self.mode in {"fixture", "mock", "offline"}:
            return MarketReference(item, "bag", 4_050, "apify_fixture", "fixture", "seeded offline reference; no external fetch")
        if self.mode != "live" or not self.token or not self.actor_id:
            raise RuntimeError("APIFY_MODE=live requires APIFY_API_TOKEN and APIFY_ACTOR_ID")
        raise RuntimeError("Apify Actor normalization is not verified; use APIFY_MODE=fixture until an official Actor schema is configured")

    @staticmethod
    def normalize_dataset_row(row: dict[str, Any], *, item: str = "coffee_beans") -> MarketReference:
        price = row.get("price_cents")
        if price is None and row.get("price") is not None:
            price = round(float(row["price"]) * 100)
        if not isinstance(price, int) or price <= 0:
            raise ValueError("dataset row requires a positive integer price_cents or numeric price")
        return MarketReference(item, str(row.get("unit", "bag")), price, "apify_actor", "normalized", str(row.get("url", "dataset row")))

    def fetch_actor_dataset(self, *, limit: int = 25) -> list[dict[str, Any]]:
        """Read an already completed Actor dataset; never starts one implicitly."""

        if self.mode != "live" or not self.token or not self.actor_id:
            raise RuntimeError("Apify live mode is not configured")
        url = f"https://api.apify.com/v2/acts/{self.actor_id}/runs/last/dataset/items"
        response = httpx.get(url, params={"limit": limit, "clean": "true"}, headers={"Authorization": f"Bearer {self.token}"}, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Apify dataset response was not a list")
        return data
