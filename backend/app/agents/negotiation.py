from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentContext, BaseBusinessAgent
from app.agents.llm_gateway import LLMGateway
from app.agents.supplier import SupplierQuote


@dataclass(frozen=True)
class NegotiationResult:
    quote: SupplierQuote
    countered: bool
    rationale: str


class NegotiationAgent(BaseBusinessAgent):
    """Compares independent supplier quotes and records bounded counteroffers."""

    role = "negotiation"

    def __init__(self, *, business_id: str, objective: str, gateway: LLMGateway | None = None) -> None:
        super().__init__(business_id=business_id, objective=objective, permissions=("read_quotes", "counter_offer"))
        self.gateway = gateway or LLMGateway(mode="replay")

    def select(self, quotes: list[SupplierQuote], context: AgentContext) -> NegotiationResult | None:
        if not quotes:
            return None
        ranked = sorted(quotes, key=lambda quote: (-quote.reliability, quote.unit_price_cents, quote.delivery_days))
        winner = ranked[0]
        countered = False
        if winner.negotiation_style == "flexible":
            decision = self.gateway.negotiate_counter({
                "supplier_id": winner.supplier_id,
                "seller_price_cents": winner.unit_price_cents,
                "buyer_limit_cents": max(0, winner.unit_price_cents - 50),
            })
            if decision.unit_price_cents < winner.unit_price_cents:
                winner = winner.with_price(decision.unit_price_cents)
                countered = True
                context.emit(
                    "CounterOfferSent",
                    business_id=self.business_id,
                    payload={"supplier_id": winner.supplier_id, "unit_price_cents": winner.unit_price_cents, "agent_id": self.agent_id, "rationale": decision.rationale},
                    idempotency_key=f"counter-sent:{self.business_id}:{winner.supplier_id}:{winner.item}:{winner.quantity}",
                )
        self.decisions += 1
        return NegotiationResult(winner, countered, "Reliability first, then price and delivery; flexible suppliers may receive a bounded counteroffer.")
