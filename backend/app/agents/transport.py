from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InProcessTransport:
    seen_keys: set[str] = field(default_factory=set)
    messages: list[dict] = field(default_factory=list)

    def send(self, message: dict) -> bool:
        key = str(message.get("idempotency_key", ""))
        if key and key in self.seen_keys:
            return False
        if key:
            self.seen_keys.add(key)
        self.messages.append(message)
        return True

    def drain(self) -> list[dict]:
        messages, self.messages = self.messages, []
        return messages


class FetchTransport(InProcessTransport):
    """Legacy local queue only. Use BusinessAgentEndpoint for actual uAgents messaging."""

    mode = "local_fetch_envelope"

