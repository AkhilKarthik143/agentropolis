from app.integrations.fetch_ai import FetchAgentTransport


def test_fetch_wire_round_trip_preserves_single_line_json():
    proposal = {"type": "OFFER", "proposal_id": "p1", "idempotency_key": "i1", "rationale": "price=stable", "metadata": {"quote": 42}}
    wire = FetchAgentTransport.encode_proposal(proposal)
    assert "PROPOSAL_JSON=" in wire
    assert FetchAgentTransport.decode_proposal(wire) == proposal

