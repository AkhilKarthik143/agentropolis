"""Market-reference adapter with a deterministic offline fixture."""

from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from statistics import median_low
from urllib.parse import quote
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
    retrieved_at: str | None = None
    sample_count: int = 1


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
        rows = self.fetch_actor_dataset()
        normalized = [self.normalize_dataset_row(row, item=item) for row in rows if row.get("item", item) == item]
        if not normalized:
            raise ValueError("completed Actor dataset has no valid rows for the requested item")
        units = {row.unit for row in normalized}
        if len(units) != 1:
            raise ValueError("cannot combine prices with different units")
        return MarketReference(item, normalized[0].unit, median_low([row.median_price_cents for row in normalized]), "apify_actor", "live",
            "; ".join(dict.fromkeys(row.provenance for row in normalized)), datetime.now(timezone.utc).isoformat(), len(normalized))

    @staticmethod
    def normalize_dataset_row(row: dict[str, Any], *, item: str = "coffee_beans") -> MarketReference:
        price = row.get("price_cents")
        if price is None and row.get("price") is not None:
            try:
                amount = Decimal(str(row["price"])) * Decimal(100)
                if not amount.is_finite():
                    raise ValueError("dataset price must be finite")
                price = int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))
            except (InvalidOperation, OverflowError) as exc:
                raise ValueError("dataset price is invalid") from exc
        if type(price) is not int or price <= 0:
            raise ValueError("dataset row requires a positive integer price_cents or numeric price")
        return MarketReference(item, str(row.get("unit", "bag")), price, "apify_actor", "normalized", str(row.get("url", "dataset row")))

    def fetch_actor_dataset(self, *, limit: int = 25) -> list[dict[str, Any]]:
        """Read an already completed Actor dataset; never starts one implicitly."""

        if self.mode != "live" or not self.token or not self.actor_id:
            raise RuntimeError("Apify live mode is not configured")
        if not 1 <= limit <= 100:
            raise ValueError("dataset reads must request 1–100 rows")
        actor = quote(self.actor_id.replace("/", "~"), safe="~")
        url = f"https://api.apify.com/v2/acts/{actor}/runs/last/dataset/items"
        response = httpx.get(url, params={"limit": limit, "clean": "true", "status": "SUCCEEDED"}, headers={"Authorization": f"Bearer {self.token}"}, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Apify dataset response was not a list")
        if any(not isinstance(row, dict) for row in data):
            raise ValueError("Apify dataset rows must be objects")
        return data
