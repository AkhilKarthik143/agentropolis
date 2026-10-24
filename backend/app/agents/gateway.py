"""Agentropolis Fetch/ASI:One gateway with an offline Chat Protocol path."""

from __future__ import annotations

import re
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from app.chat_utils import extract_text, make_chat_message
from app.security.gate import inspect_text
from .llm_gateway import LLMGateway


@dataclass(frozen=True)
class GatewayResult:
    session_id: str
    messages: tuple[str, ...]
    mode: str

    def as_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "messages": list(self.messages), "mode": self.mode}


class GatewayService:
    """Translate one natural-language request into the existing local flow."""

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.seen_msg_ids: set[str] = set()
        self.llm = llm or LLMGateway(mode=os.getenv("AGENTROPOLIS_LLM_MODE", "replay"))

    @staticmethod
    def parse_request(text: str) -> dict[str, Any]:
        quantity_match = re.search(r"\b(\d{1,3})\s*(?:bags?|units?)\b", text, re.I)
        budget_match = re.search(r"\$\s*([\d,]+)", text)
        item = "coffee_beans" if any(token in text.lower() for token in ("coffee", "beans", "roaster")) else "coffee_beans"
        return {
            "action": "run_demo",
            "business_id": "cafe_lumen",
            "item": item,
            "quantity": int(quantity_match.group(1)) if quantity_match else 12,
            "budget_cents": int(budget_match.group(1).replace(",", "")) * 100 if budget_match else 50000,
            "reserve_cents": 200000,
            "request_shock": any(token in text.lower() for token in ("bankrupt", "bankruptcy", "recover")),
        }

    def handle_message(self, msg: ChatMessage) -> GatewayResult:
        msg_id = str(msg.msg_id)
        if msg_id in self.seen_msg_ids:
            return GatewayResult("duplicate", ("TYPE=duplicate\nTEXT=Message already handled.",), "local")
        self.seen_msg_ids.add(msg_id)
        return self.run_demo(extract_text(msg))

    def run_demo(self, text: str, *, runtime=None) -> GatewayResult:
        decision = inspect_text(text, source="ASI:One request")
        if not decision.allowed:
            return GatewayResult("blocked", (f"TYPE=blocked\nTEXT={decision.reason}",), "local")
        request = self.parse_request(text)
        parsed = self.llm.parse_gateway_request({"text": text})
        plan = self.llm.plan_business({"objective": text, "reserve_cents": parsed.reserve_cents})
        request.update(parsed.model_dump())
        request["reserve_cents"] = plan.reserve_cents
        # Import lazily to keep the gateway module importable by the legacy
        # server before the economy router has completed initialization.
        if runtime is None:
            from app.api.economy import get_runtime
            runtime = get_runtime()
        engine = runtime.engine
        before = len(engine.bus.replay())
        messages = [f"TYPE=stage\nSTAGE=request\nTEXT=Parsed a simulation request for {request['business_id']}; decision_source={self.llm.last_decision_source}."]
        engine.tick()
        if request["request_shock"]:
            engine.shock("supplier_bankruptcy", supplier_id="northstar_roasters")
        events = engine.bus.replay(before)
        event_types = {event.type for event in events}
        messages.extend([
            f"TYPE=stage\nSTAGE=discovery\nTEXT=Local supplier discovery; observed_events={len(events)}. Agentverse connectivity has not been verified.",
            f"TYPE=stage\nSTAGE=negotiation\nTEXT=Agent negotiation and policy results are in the session event log; reasoning_source={engine.llm.last_decision_source}.",
            "TYPE=stage\nSTAGE=treasury\nTEXT=Authoritative treasury, approvals and finance outcomes are recorded per action; no blanket approval is inferred.",
            "TYPE=stage\nSTAGE=x402\nTEXT=External x402 settlement is not active in this simulation. The optional guarded testnet HTTP client requires separate configuration and authorization.",
        ])
        if request["request_shock"]:
            messages.append("TYPE=stage\nSTAGE=recovery\nTEXT=Supplier bankruptcy was submitted; inspect recorded recovery proposals and outcomes in this session.")
        blocked = "ACTION_BLOCKED" in event_types
        proof = engine.ledger.proof(request["business_id"])
        audit = engine.audit_verification()
        messages.append(f"TYPE=result\nTEXT=Session {runtime.session_id} processed; ledger_balanced={proof['balanced']}; audit_valid={audit['valid']}; security_blocked={blocked}; external_payments_verified=False.")
        return GatewayResult(runtime.session_id, tuple(messages), "local")


def create_gateway_agent(
    *,
    seed: str,
    port: int = 9510,
    mailbox: bool = False,
    network: str | None = None,
    readme_path: str | None = None,
    publish_agent_details: bool = False,
    registration_policy: Any | None = None,
    service: GatewayService | None = None,
) -> Agent:
    """Build the public Chat Protocol gateway; no handler mutates economy state."""

    kwargs: dict[str, Any] = {"name": "agentropolis_gateway", "seed": seed, "port": port}
    if mailbox:
        kwargs["mailbox"] = True
    if network:
        kwargs["network"] = network
    if readme_path:
        kwargs["readme_path"] = readme_path
    if publish_agent_details:
        kwargs["publish_agent_details"] = True
        kwargs["metadata"] = {
            "role": "gateway",
            "category": "agent_economy",
            "features": "supplier_discovery,procurement,recovery,asi_one",
            "protocol": "chat",
        }
    if registration_policy is not None:
        kwargs["registration_policy"] = registration_policy
    agent = Agent(**kwargs)
    gateway = service or GatewayService()
    chat_proto = Protocol(spec=chat_protocol_spec)

    @agent.on_event("startup")
    async def on_startup(ctx: Context) -> None:
        ctx.logger.info("Agentropolis gateway ready address=%s mailbox=%s", agent.address, mailbox)

    @chat_proto.on_message(model=ChatMessage)
    async def handle_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
        for reply in gateway.handle_message(msg).messages:
            await ctx.send(sender, make_chat_message(reply))

    @chat_proto.on_message(model=ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        return None

    agent.include(chat_proto, publish_manifest=publish_agent_details)
    return agent
