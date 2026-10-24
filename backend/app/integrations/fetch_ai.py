from __future__ import annotations

from dataclasses import dataclass
import json

from app.agents.transport import FetchTransport, InProcessTransport
from app.chat_utils import make_chat_message, parse_fields


@dataclass
class FetchAgentTransport:
    mode: str = "inprocess"

    def __post_init__(self) -> None:
        self.transport = FetchTransport() if self.mode == "fetch" else InProcessTransport()

    def send_proposal(self, proposal: dict) -> bool:
        return self.transport.send({"type": "proposal", "proposal": proposal, "idempotency_key": proposal.get("idempotency_key")})

    @staticmethod
    def encode_proposal(proposal: dict) -> str:
        """Encode one-line JSON so legacy Chat Protocol field parsing is lossless."""
        return "TYPE=proposal\nRID={}\nPROPOSAL_JSON={}".format(proposal.get("deal_id") or proposal.get("proposal_id", ""), json.dumps(proposal, separators=(",", ":"), sort_keys=True))

    @staticmethod
    def decode_proposal(text: str) -> dict:
        fields = parse_fields(text)
        if fields.get("TYPE", "").upper() != "PROPOSAL" or not fields.get("PROPOSAL_JSON"):
            raise ValueError("not a proposal message")
        return json.loads(fields["PROPOSAL_JSON"])

    @classmethod
    def make_message(cls, proposal: dict):
        return make_chat_message(cls.encode_proposal(proposal))


# These models run on the real uAgents protocol stack. They are separate from
# the legacy Chat Protocol serialization helper above.
from datetime import datetime, timezone
import hashlib
import inspect
from pathlib import Path
import sqlite3
from typing import Any, Callable

import httpx
from uagents import Agent, Context, Model, Protocol
from uagents.registration import AgentRegistrationPolicy
from app.events.schemas import AgentMessage


class BusinessWireMessage(Model):
    envelope: dict[str, Any]


class BusinessDeliveryAck(Model):
    message_id: str
    status: str
    detail: str = "Delivery acknowledgement is not economic execution."


class CapabilityQuery(Model):
    requested_role: str = ""


class CapabilityAdvertisement(Model):
    agent_id: str
    business_id: str
    role: str
    capabilities: list[str]
    protocol_digest: str
    mode: str


class LocalOnlyRegistration(AgentRegistrationPolicy):
    async def register(self, *args: Any, **kwargs: Any) -> None:
        """Do not publish, request faucet funds or register on chain in local mode."""
        return None


class LocalBusinessUAgent(Agent):
    async def _update_agent_status(self, active: bool) -> None:
        # uAgents 0.23 sends a status request even with publication/telemetry off.
        # Local verification must not silently contact Agentverse.
        return None


class BusinessAgentEndpoint:
    """Authenticated typed ingress for one business-owned uAgent.

    The host must supply a trusted peer-address directory and a handler that
    submits work to its deterministic runtime. Discovery results are observations,
    never automatically trusted peers or execution permission.
    """

    def __init__(self, *, agent_id: str, business_id: str, role: str, simulation_id: str,
                 seed: str, handler: Callable[[AgentMessage], Any],
                 peers: dict[str, dict[str, str]] | None = None,
                 capabilities: tuple[str, ...] = (), port: int = 9511,
                 endpoint: str | None = None, register: bool = False,
                 inbox_path: str = ".data/fetch-inbox.sqlite3") -> None:
        if not seed or seed.startswith("your_"):
            raise ValueError("a private persistent agent seed is required")
        if register and (not endpoint or not endpoint.startswith("https://")):
            raise ValueError("public registration requires an explicit reachable HTTPS endpoint")
        self.agent_id, self.business_id, self.role = agent_id, business_id, role
        self.simulation_id, self.handler, self.peers = simulation_id, handler, peers or {}
        self.capabilities = list(capabilities)
        self.mode = "network_configured_unverified" if register else "local_uagents"
        self.inbox_path = inbox_path
        Path(inbox_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(inbox_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS fetch_inbox (recipient TEXT, session TEXT, key TEXT, fingerprint TEXT, status TEXT, PRIMARY KEY(recipient,session,key))")
        # Derivation makes identities independent by role, business and session,
        # while stable across restart with the same private seed.
        private_seed = hashlib.sha256(f"{seed}:{simulation_id}:{business_id}:{agent_id}".encode()).hexdigest()
        agent_class = Agent if register else LocalBusinessUAgent
        self.agent = agent_class(name=agent_id, seed=private_seed, port=port, endpoint=endpoint,
            network="testnet", registration_policy=None if register else LocalOnlyRegistration(),
            publish_agent_details=register, enable_agent_inspector=False, report_events=register,
            metadata={"business_id": business_id, "role": role, "capabilities": self.capabilities})
        self.protocol = Protocol(name="AgentropolisBusiness", version="1.0.0")

        @self.protocol.on_message(model=BusinessWireMessage, replies=BusinessDeliveryAck)
        async def receive(ctx: Context, sender: str, msg: BusinessWireMessage) -> None:
            ack = await self.accept(sender, msg)
            await ctx.send(sender, ack)

        @self.protocol.on_message(model=BusinessDeliveryAck)
        async def ack(ctx: Context, sender: str, msg: BusinessDeliveryAck) -> None:
            # Execution status is supplied separately by business messages.
            return None

        @self.protocol.on_message(model=CapabilityQuery, replies=CapabilityAdvertisement)
        async def advertise(ctx: Context, sender: str, msg: CapabilityQuery) -> None:
            if not msg.requested_role or msg.requested_role == self.role:
                await ctx.send(sender, CapabilityAdvertisement(agent_id=self.agent_id,
                    business_id=self.business_id, role=self.role, capabilities=self.capabilities,
                    protocol_digest=self.protocol.digest, mode=self.mode))

        @self.protocol.on_message(model=CapabilityAdvertisement)
        async def advertisement(ctx: Context, sender: str, msg: CapabilityAdvertisement) -> None:
            return None

        self.agent.include(self.protocol, publish_manifest=register)

    @property
    def address(self) -> str:
        return self.agent.address

    async def accept(self, sender_address: str, wire: BusinessWireMessage) -> BusinessDeliveryAck:
        message_id = str(wire.envelope.get("message_id", "invalid"))
        reserved = False
        try:
            msg = AgentMessage.model_validate(wire.envelope)
            peer = self.peers.get(sender_address)
            if not peer or peer.get("agent_id") != msg.sender_id or peer.get("business_id") != msg.business_id:
                raise ValueError("sender identity does not match trusted network peer")
            if msg.recipient_id != self.agent_id or msg.simulation_id != self.simulation_id or msg.schema_version != 1:
                raise ValueError("recipient, simulation or schema mismatch")
            if msg.expires_at and (msg.expires_at.tzinfo is None or msg.expires_at <= datetime.now(timezone.utc)):
                raise ValueError("message expired or has no timezone")
            encoded = json.dumps(msg.model_dump(mode="json"), sort_keys=True)
            if len(encoded.encode()) > 64000:
                raise ValueError("message exceeds size limit")
            fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
            with sqlite3.connect(self.inbox_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT fingerprint,status FROM fetch_inbox WHERE recipient=? AND session=? AND key=?", (self.agent_id, self.simulation_id, msg.idempotency_key)).fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise ValueError("idempotency key reused with changed message")
                    return BusinessDeliveryAck(message_id=msg.message_id, status="duplicate" if row[1] == "delivered" else "uncertain")
                conn.execute("INSERT INTO fetch_inbox VALUES (?,?,?,?,?)", (self.agent_id, self.simulation_id, msg.idempotency_key, fingerprint, "pending"))
            reserved = True
            value = self.handler(msg)
            if inspect.isawaitable(value):
                await value
            with sqlite3.connect(self.inbox_path) as conn:
                conn.execute("UPDATE fetch_inbox SET status='delivered' WHERE recipient=? AND session=? AND key=?", (self.agent_id, self.simulation_id, msg.idempotency_key))
            return BusinessDeliveryAck(message_id=msg.message_id, status="delivered")
        except Exception as exc:
            # Do not echo arbitrary supplier content or provider error bodies.
            return BusinessDeliveryAck(message_id=message_id, status="uncertain" if reserved else "rejected", detail=type(exc).__name__)

    async def send(self, ctx: Context, destination: str, message: AgentMessage) -> Any:
        peer = self.peers.get(destination)
        if not peer or peer.get("agent_id") != message.recipient_id:
            raise ValueError("recipient address is not an approved peer")
        if message.sender_id != self.agent_id or message.business_id != self.business_id or message.simulation_id != self.simulation_id:
            raise ValueError("outgoing message does not belong to this identity")
        return await ctx.send(destination, BusinessWireMessage(envelope=message.model_dump(mode="json")))


class AgentverseDiscovery:
    """Official search endpoint. Untrusted observations require owner verification."""

    def search(self, query: str, *, protocol_digest: str, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip() or not protocol_digest.startswith("proto:") or not 1 <= limit <= 25:
            raise ValueError("query, protocol digest and bounded limit are required")
        try:
            response = httpx.post("https://agentverse.ai/v1/search/agents", json={
                "search_text": query, "sort": "relevancy", "filters": {"protocol_digest": [protocol_digest]},
                "direction": "asc", "offset": 0, "limit": limit}, timeout=10)
            response.raise_for_status()
            rows = response.json().get("agents", [])
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("invalid discovery response")
            return rows
        except (httpx.HTTPError, ValueError):
            raise RuntimeError("Agentverse discovery unavailable; no network suppliers verified") from None
