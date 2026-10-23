from __future__ import annotations

from .engine import EconomyEngine


SUPPORTED_SHOCKS = ("supplier_bankruptcy", "demand_spike", "shortage", "suspicious_invoice", "failed_payment", "liquidity_crisis")


def inject(engine: EconomyEngine, shock_type: str, supplier_id: str | None = None) -> dict:
    normalized = shock_type.lower()
    aliases = {"supplier_bankruptcy": "supplier_bankruptcy", "supplier_bankrupt": "supplier_bankruptcy"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_SHOCKS:
        raise ValueError(f"unknown shock: {shock_type}")
    return engine.shock(normalized, supplier_id=supplier_id)

