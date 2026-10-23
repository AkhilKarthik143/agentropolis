"""Small deterministic gate used before agent text, LLM calls, and proposals."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|your)\s+(instructions|rules)", re.I),
    re.compile(r"wire\s+(the\s+)?(full|entire)\s+balance", re.I),
    re.compile(r"bypass\s+(approval|policy|reserve)", re.I),
    re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.I),
)

MUTATING_TOKENS = frozenset({
    "write_cash", "write_inventory", "write_contract", "write_ledger",
    "set_supplier_status", "transfer_money", "post_journal_entry",
})


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str = ""
    code: str = "OK"


def inspect_text(text: str, *, source: str = "agent") -> GateDecision:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text or ""):
            return GateDecision(False, f"prompt-injection pattern detected in {source} text", "PROMPT_INJECTION")
    return GateDecision(True)


def inspect_tool(name: str, allowed_tools: Iterable[str]) -> GateDecision:
    normalized = str(name).strip()
    if normalized in MUTATING_TOKENS or normalized not in set(allowed_tools):
        return GateDecision(False, f"tool is not allowlisted: {normalized}", "UNAUTHORIZED_TOOL")
    return GateDecision(True)


def inspect_callable(callable_obj: Callable[..., Any], allowed_tools: Iterable[str]) -> GateDecision:
    name = getattr(callable_obj, "__name__", repr(callable_obj))
    # Private implementation helpers are still safe when their public tool
    # name is explicitly allowlisted by the gateway.
    public_name = name.lstrip("_")
    return inspect_tool(public_name, allowed_tools)


def inspect_proposal(proposal: Any) -> GateDecision:
    quantity = getattr(proposal, "quantity", None)
    unit_price = getattr(proposal, "unit_price_cents", None)
    total = getattr(proposal, "total_cents", None)
    if quantity is not None and quantity <= 0:
        return GateDecision(False, "proposal quantity must be positive", "SCHEMA_INVALID")
    if unit_price is not None and unit_price < 0:
        return GateDecision(False, "proposal unit price cannot be negative", "FINANCIAL_INVALID")
    if total is not None and total < 0:
        return GateDecision(False, "proposal total cannot be negative", "FINANCIAL_INVALID")
    metadata = getattr(proposal, "metadata", {}) or {}
    text = str(metadata.get("supplier_note", ""))
    if text:
        decision = inspect_text(text, source="supplier")
        if not decision.allowed:
            return decision
    return GateDecision(True)
