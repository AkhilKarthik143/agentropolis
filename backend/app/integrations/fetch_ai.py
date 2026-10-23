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

