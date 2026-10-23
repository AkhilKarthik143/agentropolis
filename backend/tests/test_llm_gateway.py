from app.agents.llm_gateway import LLMGateway


def test_invalid_llm_output_retries_once_then_uses_heuristic():
    gateway = LLMGateway(responses=["not-json", {"type": "not-a-proposal"}])
    proposal = gateway.propose({"business_id": "buyer", "counterparty_id": "seller", "item": "beans", "quantity": 2, "unit_price_cents": 100})
    assert gateway.attempts == 2
    assert proposal.item == "beans"
    assert "fallback" in proposal.private_rationale

