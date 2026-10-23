"""Transparent, deterministic offer scoring for the buyer-facing UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreWeights:
    price: float = 0.35
    delivery: float = 0.20
    reliability: float = 0.30
    owner_preference: float = 0.15


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_offer(
    offer: dict[str, Any],
    *,
    owner_preferences: dict[str, Any] | None = None,
    weights: ScoreWeights | None = None,
) -> dict[str, Any]:
    """Return a 0-100 score and per-factor contributions."""

    preferences = owner_preferences or {}
    weights = weights or ScoreWeights()
    price_cents = max(0, int(offer.get("price_cents", offer.get("unit_price_cents", 0))))
    reference_price = max(1, int(preferences.get("reference_price_cents", 5_000)))
    delivery_days = max(0, int(offer.get("delivery_days", 0)))
    reliability = _clamp(float(offer.get("reliability", 0.0)))
    required_reliability = _clamp(float(preferences.get("required_reliability", 0.0)))
    preferred_delivery = max(0, int(preferences.get("preferred_delivery_days", 2)))

    price_raw = _clamp(1.0 - ((price_cents - reference_price) / reference_price))
    delivery_raw = _clamp(1.0 - (max(0, delivery_days - preferred_delivery) / 7.0))
    preference_raw = _clamp(
        (0.65 if reliability >= required_reliability else 0.0)
        + (0.35 if delivery_days <= preferred_delivery else 0.0)
    )
    factors = {
        "price": {"raw": price_raw, "weight": weights.price, "contribution": price_raw * weights.price},
        "delivery": {"raw": delivery_raw, "weight": weights.delivery, "contribution": delivery_raw * weights.delivery},
        "reliability": {"raw": reliability, "weight": weights.reliability, "contribution": reliability * weights.reliability},
        "owner_preference": {"raw": preference_raw, "weight": weights.owner_preference, "contribution": preference_raw * weights.owner_preference},
    }
    return {
        "score": round(sum(item["contribution"] for item in factors.values()) * 100, 2),
        "factors": factors,
        "inputs": {
            "price_cents": price_cents,
            "delivery_days": delivery_days,
            "reliability": reliability,
            "required_reliability": required_reliability,
            "preferred_delivery_days": preferred_delivery,
        },
    }
