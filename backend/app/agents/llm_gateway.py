"""One structured reasoning boundary for Claude-compatible decisions.

The gateway can be switched to live/record/replay without giving a model a
reference to the economy engine. The deterministic engine still validates and
executes every proposal.
"""

from __future__ import annotations

import json
import re
import asyncio
import os
from threading import Thread
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.events.schemas import Proposal, ProposalType
from app.security.gate import inspect_callable, inspect_text


class DecisionKind(StrEnum):
    OFFER_COMPARISON = "offer_comparison"
    NEGOTIATION_COUNTER = "negotiation_counter"
    RISK_EXPLANATION = "risk_explanation"
    RECOVERY_PLANNING = "recovery_planning"
    BUSINESS_PLANNING = "business_planning"
    GATEWAY_REQUEST_PARSING = "gateway_request_parsing"


class OfferComparisonDecision(BaseModel):
    selected_supplier_id: str = ""
    rationale: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class NegotiationCounterDecision(BaseModel):
    unit_price_cents: int = Field(ge=0)
    rationale: str = ""
    within_seller_bounds: bool = True


class RiskExplanationDecision(BaseModel):
    decision: str = "APPROVE"
    reason: str = ""
    policy_checks: list[str] = Field(default_factory=list)


class RecoveryPlanDecision(BaseModel):
    ranked_supplier_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    recovery_action: str = "replace_supplier"


class BusinessPlanDecision(BaseModel):
    objective: str = "maintain reserve and source reliable suppliers"
    reserve_cents: int = Field(default=200_000, ge=0)
    required_reliability: float = Field(default=0.7, ge=0.0, le=1.0)


class GatewayRequestDecision(BaseModel):
    item: str = "coffee_beans"
    quantity: int = Field(default=12, ge=1)
    budget_cents: int = Field(default=50_000, ge=0)
    reserve_cents: int = Field(default=200_000, ge=0)
    request_shock: bool = False


DECISION_SCHEMAS = {
    DecisionKind.OFFER_COMPARISON: OfferComparisonDecision,
    DecisionKind.NEGOTIATION_COUNTER: NegotiationCounterDecision,
    DecisionKind.RISK_EXPLANATION: RiskExplanationDecision,
    DecisionKind.RECOVERY_PLANNING: RecoveryPlanDecision,
    DecisionKind.BUSINESS_PLANNING: BusinessPlanDecision,
    DecisionKind.GATEWAY_REQUEST_PARSING: GatewayRequestDecision,
}

READ_ONLY_TOOLS: tuple[str, ...] = (
    "read_business_snapshot",
    "read_supplier_quotes",
    "read_policy_limits",
    "read_recovery_candidates",
)


def _read_business_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    return dict(context.get("business", {}))


def _read_supplier_quotes(context: dict[str, Any]) -> list[dict[str, Any]]:
    return list(context.get("offers", []))


def _read_policy_limits(context: dict[str, Any]) -> dict[str, Any]:
    return {key: context[key] for key in ("reserve_cents", "spend_limit_cents") if key in context}


def _read_recovery_candidates(context: dict[str, Any]) -> list[str]:
    return list(context.get("replacement_candidates", []))


_TOOL_CALLABLES: dict[str, Callable[..., Any]] = {
    "read_business_snapshot": _read_business_snapshot,
    "read_supplier_quotes": _read_supplier_quotes,
    "read_policy_limits": _read_policy_limits,
    "read_recovery_candidates": _read_recovery_candidates,
}


def tools_for(kind: DecisionKind | str) -> tuple[str, ...]:
    DecisionKind(kind)
    return READ_ONLY_TOOLS


def tool_callables_for(kind: DecisionKind | str) -> tuple[Callable[..., Any], ...]:
    names = tools_for(kind)
    callables = tuple(_TOOL_CALLABLES[name] for name in names)
    for callable_obj in callables:
        decision = inspect_callable(callable_obj, names)
        if not decision.allowed:
            raise RuntimeError(decision.reason)
    return callables


@dataclass
class LLMGateway:
    """Structured Claude seam with deterministic fallback and one retry."""

    mode: str = "live"
    responses: list[str | dict[str, Any]] = field(default_factory=list)
    fallback: Callable[[dict[str, Any]], Proposal] | None = None
    attempts: int = 0
    calls: list[DecisionKind] = field(default_factory=list)
    recordings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in {"live", "record", "replay"}:
            raise ValueError("LLM mode must be live, record, or replay")

    def propose(self, context: dict[str, Any]) -> Proposal:
        """Legacy proposal API retained for Stage 1 callers."""

        self.attempts = 0
        for _ in range(2):
            self.attempts += 1
            raw = self.responses.pop(0) if self.responses else None
            try:
                if raw is None:
                    raise ValueError("no configured LLM response")
                if isinstance(raw, str) and not inspect_text(raw, source="LLM output").allowed:
                    raise ValueError("LLM output blocked by security gate")
                data = json.loads(raw) if isinstance(raw, str) else raw
                return Proposal.model_validate(data)
            except Exception:
                continue
        if self.fallback:
            return self.fallback(context)
        return self.heuristic(context)

    def _structured(self, kind: DecisionKind, context: dict[str, Any]) -> BaseModel:
        decision = inspect_text(json.dumps(context, sort_keys=True), source="LLM input")
        if not decision.allowed:
            raise ValueError(decision.reason)
        tool_callables_for(kind)
        self.calls.append(kind)
        schema = DECISION_SCHEMAS[kind]
        key = kind.value
        if self.mode == "replay" and key in self.recordings:
            return schema.model_validate(self.recordings[key])
        for _ in range(2):
            raw = self.responses.pop(0) if self.responses else None
            try:
                if raw is None:
                    if self.mode in {"live", "record"}:
                        raw = self._live_json(kind, context)
                    else:
                        raise ValueError("no configured structured response")
                if isinstance(raw, str) and not inspect_text(raw, source="LLM output").allowed:
                    raise ValueError("LLM output blocked by security gate")
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                result = schema.model_validate(parsed)
                if self.mode == "record":
                    self.recordings[key] = result.model_dump()
                return result
            except Exception:
                continue
        result = self._heuristic_decision(kind, context)
        if self.mode == "record":
            self.recordings[key] = result.model_dump()
        return result

    @staticmethod
    def _live_json(kind: DecisionKind, context: dict[str, Any]) -> str:
        """Call the existing Claude boundary without exposing engine tools.

        Economy commands are synchronous, while FastAPI may invoke them on an
        active event loop.  A short worker thread keeps the adapter usable in
        both the CLI and HTTP paths; failures are caught by the normal retry
        and deterministic fallback path above.
        """

        from app.chat_utils import generate_text

        async def request() -> str:
            return await generate_text(
                "Return JSON only. Follow the requested decision schema exactly. Never propose a state mutation or a tool call.",
                json.dumps({"decision_kind": kind.value, "context": context}, sort_keys=True),
                max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "400")),
                temperature=0.0,
                strict=True,
                provider="claude",
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(request())

        result: list[str] = []
        error: list[BaseException] = []

        def worker() -> None:
            try:
                result.append(asyncio.run(request()))
            except BaseException as exc:  # surfaced to the normal fallback
                error.append(exc)

        thread = Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=float(os.getenv("CLAUDE_TIMEOUT_SECONDS", "12")))
        if thread.is_alive():
            raise TimeoutError("Claude structured call timed out")
        if error:
            raise error[0]
        if not result:
            raise RuntimeError("Claude structured call returned no result")
        return result[0]

    def _heuristic_decision(self, kind: DecisionKind, context: dict[str, Any]) -> BaseModel:
        if kind is DecisionKind.OFFER_COMPARISON:
            offers = list(context.get("offers", []))
            selected = max(offers, key=lambda offer: (float(offer.get("reliability", 0)), -int(offer.get("price_cents", 0))), default={})
            return OfferComparisonDecision(selected_supplier_id=str(selected.get("supplier_id", "")), rationale="Deterministic fallback ranked reliability before price.", confidence=0.5)
        if kind is DecisionKind.NEGOTIATION_COUNTER:
            seller = int(context.get("seller_price_cents", 0))
            buyer = int(context.get("buyer_limit_cents", seller))
            return NegotiationCounterDecision(unit_price_cents=max(0, min(seller, buyer)), rationale="Counter stays inside the supplied seller and buyer bounds.", within_seller_bounds=True)
        if kind is DecisionKind.RISK_EXPLANATION:
            validation = context.get("validation", {})
            return RiskExplanationDecision(decision="APPROVE", reason="Deterministic reserve, spend, and reliability checks passed.", policy_checks=[str(validation.get("stage", "validated")), "engine_only_writer"])
        if kind is DecisionKind.BUSINESS_PLANNING:
            text = str(context.get("objective", "")).lower()
            return BusinessPlanDecision(
                objective="maintain reserve and avoid unreliable suppliers" if "reserve" in text or "reliable" in text else "maintain reserve and source reliable suppliers",
                reserve_cents=max(0, int(context.get("reserve_cents", 200_000))),
                required_reliability=0.7,
            )
        if kind is DecisionKind.GATEWAY_REQUEST_PARSING:
            text = str(context.get("text", ""))
            quantity_match = re.search(r"\b(\d{1,3})\s*(?:bags?|units?)\b", text, re.I)
            budget_match = re.search(r"\$\s*([\d,]+)", text)
            lowered = text.lower()
            return GatewayRequestDecision(
                item="coffee_beans",
                quantity=int(quantity_match.group(1)) if quantity_match else 12,
                budget_cents=int(budget_match.group(1).replace(",", "")) * 100 if budget_match else 50_000,
                reserve_cents=200_000,
                request_shock=any(token in lowered for token in ("bankrupt", "bankruptcy", "recover")),
            )
        return RecoveryPlanDecision(ranked_supplier_ids=[str(item) for item in context.get("replacement_candidates", [])], rationale="Fallback selected the available replacement candidates by policy.")

    def compare_offers(self, context: dict[str, Any]) -> OfferComparisonDecision:
        return self._structured(DecisionKind.OFFER_COMPARISON, context)  # type: ignore[return-value]

    def negotiate_counter(self, context: dict[str, Any]) -> NegotiationCounterDecision:
        return self._structured(DecisionKind.NEGOTIATION_COUNTER, context)  # type: ignore[return-value]

    def explain_risk(self, context: dict[str, Any]) -> RiskExplanationDecision:
        return self._structured(DecisionKind.RISK_EXPLANATION, context)  # type: ignore[return-value]

    def plan_recovery(self, context: dict[str, Any]) -> RecoveryPlanDecision:
        return self._structured(DecisionKind.RECOVERY_PLANNING, context)  # type: ignore[return-value]

    def plan_business(self, context: dict[str, Any]) -> BusinessPlanDecision:
        return self._structured(DecisionKind.BUSINESS_PLANNING, context)  # type: ignore[return-value]

    def parse_gateway_request(self, context: dict[str, Any]) -> GatewayRequestDecision:
        return self._structured(DecisionKind.GATEWAY_REQUEST_PARSING, context)  # type: ignore[return-value]

    @staticmethod
    def heuristic(context: dict[str, Any]) -> Proposal:
        quantity = max(1, int(context.get("quantity", 1)))
        unit_price = max(1, int(context.get("unit_price_cents", 100)))
        return Proposal(
            type=ProposalType.OFFER, agent_id=str(context.get("agent_id", "heuristic_procurement_agent")),
            business_id=str(context["business_id"]), counterparty_id=str(context["counterparty_id"]),
            item=str(context.get("item", "goods")), quantity=quantity, unit="unit",
            unit_price_cents=unit_price, total_cents=quantity * unit_price, delivery_days=int(context.get("delivery_days", 2)),
            public_rationale="Deterministic fallback prioritized a valid offer within policy.",
            private_rationale="No verified LLM response was available; heuristic fallback used.",
        )
