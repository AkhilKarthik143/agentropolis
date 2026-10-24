"""Provider contract tests use HTTP fixtures; none claim live verification."""
import asyncio
import base64
import json
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import httpx
import pytest
from app.agents.llm_gateway import LLMGateway
from app.events.schemas import AgentMessage
from app.integrations.nessie import NessieBank, NessieUncertainError
from app.integrations.coinbase_x402 import MockX402, X402HTTPClient, X402UncertainError, BASE_SEPOLIA, BASE_SEPOLIA_USDC
from app.integrations.fetch_ai import BusinessAgentEndpoint, BusinessWireMessage
from app.integrations.apify import ApifySupplierIntel


def test_llm_rejects_unknown_supplier_and_execution_fields():
    gateway = LLMGateway(responses=[{"selected_supplier_id": "outsider"}, {"selected_supplier_id": "seller", "execute_payment": True}])
    choice = gateway.compare_offers({"offers": [{"supplier_id": "seller", "reliability": 0.9, "price_cents": 50}]})
    assert choice.selected_supplier_id == "seller"
    assert gateway.last_decision_source == "deterministic_fallback"
    assert len(gateway.audit_records[-1]["errors"]) == 2


def test_context_bound_replay_and_infeasible_counter():
    gateway = LLMGateway(mode="record", responses=[{"selected_supplier_id": "a"}])
    ctx = {"offers": [{"supplier_id": "a"}]}
    gateway.compare_offers(ctx)
    gateway.mode = "replay"
    gateway.compare_offers(ctx)
    assert gateway.last_decision_source == "replay"
    assert gateway.compare_offers({"offers": [{"supplier_id": "b"}]}).selected_supplier_id == "b"
    assert gateway.last_decision_source == "deterministic_fallback"
    result = gateway.negotiate_counter({"seller_floor_cents": 200, "seller_price_cents": 300, "buyer_limit_cents": 100})
    assert result.within_seller_bounds is False and result.unit_price_cents <= 100


def test_zero_llm_budget_blocks_sdk_call(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "fixture-secret-not-real")
    gateway = LLMGateway(mode="live", budget_microdollars=0)
    gateway.plan_business({"reserve_cents": 1000})
    assert gateway.live_calls == 0 and gateway.last_decision_source == "deterministic_fallback"
    assert gateway.audit_records[-1]["errors"] == ["PermissionError"]


def test_llm_usage_and_role_schema_passed_to_sdk(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "fixture-secret-not-real")
    seen = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self.messages = self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def parse(self, **kwargs):
            seen.append(kwargs)
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=20), parsed_output=kwargs["output_format"](selected_supplier_id="seller"))
    monkeypatch.setattr("anthropic.Anthropic", Client)
    gateway = LLMGateway(mode="live")
    gateway.compare_offers({"offers": [{"supplier_id": "seller"}]})
    assert "Procurement" in seen[0]["system"] and gateway.last_decision_source == "live"
    assert gateway.usage_summary()["input_tokens"] == 100
    assert gateway.reserved_microdollars >= gateway.measured_microdollars > 0


def test_nessie_auth_exact_cents_and_durable_duplicate(tmp_path):
    calls = []
    def respond(request):
        calls.append(request)
        assert request.url.params["key"] == "fixture-key" and "api-key" not in request.headers
        if request.method == "POST":
            assert b'"amount":10.01' in request.content
            return httpx.Response(201, json={"code": 201, "objectCreated": {"_id": "transfer1", "status": "pending"}})
        return httpx.Response(200, json={"_id": "account", "balance": "10.01"})
    options = dict(api_key="fixture-key", journal_path=str(tmp_path / "bank.db"), client=httpx.Client(transport=httpx.MockTransport(respond)))
    bank = NessieBank(**options)
    assert bank.balance_cents("account") == 1001
    assert bank.transfer("a", "b", 1001, "test", "key")["status"] == "pending"
    restarted = NessieBank(**options)
    assert restarted.transfer("a", "b", 1001, "test", "key")["_id"] == "transfer1"
    assert len(calls) == 2
    with pytest.raises(ValueError, match="different"):
        restarted.transfer("a", "b", 1002, "test", "key")


def test_nessie_timeout_never_resubmits_or_leaks_key(tmp_path):
    requests = []
    def fail(request):
        requests.append(request)
        raise httpx.ReadTimeout("sensitive fixture-key URL", request=request)
    bank = NessieBank(api_key="fixture-key", journal_path=str(tmp_path / "bank.db"), client=httpx.Client(transport=httpx.MockTransport(fail)))
    for _ in range(2):
        with pytest.raises(NessieUncertainError) as caught:
            bank.transfer("a", "b", 1, "test", "same")
        assert "fixture-key" not in str(caught.value)
    assert len(requests) == 1


def test_fetch_independent_identity_sender_binding_and_durable_inbox(tmp_path):
    async def run():
        received = []
        common = dict(simulation_id="s", seed="private-fixture", inbox_path=str(tmp_path / "inbox.db"))
        buyer = BusinessAgentEndpoint(agent_id="buyer", business_id="b", role="procurement", handler=lambda msg: None, **common)
        seller = BusinessAgentEndpoint(agent_id="seller", business_id="s", role="sales", handler=received.append, **common)
        assert buyer.address != seller.address
        seller.peers[buyer.address] = {"agent_id": "buyer", "business_id": "b"}
        message = AgentMessage(sender_id="buyer", recipient_id="seller", business_id="b", simulation_id="s", message_type="REQUEST_FOR_QUOTE", payload={"item": "flour"})
        wire = BusinessWireMessage(envelope=message.model_dump(mode="json"))
        assert (await seller.accept("agent1-untrusted", wire)).status == "rejected"
        assert (await seller.accept(buyer.address, wire)).status == "delivered"
        assert (await seller.accept(buyer.address, wire)).status == "duplicate" and len(received) == 1
        restarted = BusinessAgentEndpoint(agent_id="seller", business_id="s", role="sales", handler=received.append, peers=seller.peers, **common)
        assert restarted.address == seller.address
        assert (await restarted.accept(buyer.address, wire)).status == "duplicate"
        message.idempotency_key = "expired"
        message.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert (await seller.accept(buyer.address, BusinessWireMessage(envelope=message.model_dump(mode="json")))).status == "rejected"
    asyncio.run(run())


def test_apify_completed_dataset_and_decimal_prices(monkeypatch):
    def get(url, **kwargs):
        assert kwargs["params"]["status"] == "SUCCEEDED" and "vendor~catalog" in url
        return httpx.Response(200, request=httpx.Request("GET", url), json=[{"price": "10.005", "url": "https://example.com/a"}, {"price_cents": 1200, "url": "https://example.com/b"}])
    monkeypatch.setattr(httpx, "get", get)
    result = ApifySupplierIntel(mode="live", token="fixture", actor_id="vendor/catalog").market_reference()
    assert result.median_price_cents == 1001 and result.sample_count == 2
    assert result.mode == "live" and result.retrieved_at


def header(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


def challenge(url, pay_to, **overrides):
    return {"x402Version": 2, "resource": {"url": url}, "accepts": [{"scheme": "exact", "network": BASE_SEPOLIA, "asset": BASE_SEPOLIA_USDC, "amount": "10000", "payTo": pay_to, "maxTimeoutSeconds": 60, **overrides}]}


def test_x402_rejects_mainnet_recipient_and_overspend_before_signing(tmp_path):
    url, recipient = "https://service.example/report", "0x" + "1" * 40
    for index, changes in enumerate([{"network": "eip155:8453"}, {"payTo": "0x" + "2" * 40}, {"amount": "20000"}]):
        signed = []
        http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(402, headers={"PAYMENT-REQUIRED": header(challenge(url, recipient, **changes))})))
        buyer = X402HTTPClient(allowed_origin="https://service.example", pay_to=recipient, signer=lambda value: signed.append(value), client=http, journal_path=str(tmp_path / f"pay{index}.db"))
        with pytest.raises(ValueError):
            buyer.purchase(url, authorized_cents=1, idempotency_key="p")
        assert not signed


def test_x402_uncertain_submission_survives_restart(tmp_path):
    url, recipient = "https://service.example/report", "0x" + "1" * 40
    calls = []
    def handle(req):
        calls.append(req)
        if "PAYMENT-SIGNATURE" in req.headers:
            raise httpx.ReadTimeout("timeout", request=req)
        return httpx.Response(402, headers={"PAYMENT-REQUIRED": header(challenge(url, recipient))})
    options = dict(allowed_origin="https://service.example", pay_to=recipient, signer=lambda value: "test-signature", client=httpx.Client(transport=httpx.MockTransport(handle)), journal_path=str(tmp_path / "pay.db"))
    for _ in range(2):
        with pytest.raises(X402UncertainError):
            X402HTTPClient(**options).purchase(url, authorized_cents=1, idempotency_key="same")
    assert len(calls) == 2


def test_mock_payment_rejects_changed_terms():
    rail = MockX402()
    rail.pay(10, "key")
    with pytest.raises(ValueError, match="different"):
        rail.pay(20, "key")
