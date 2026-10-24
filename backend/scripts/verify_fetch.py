#!/usr/bin/env python3
"""Verify two independent uAgents exchange a typed business message locally.

No registration, faucet, Agentverse, wallet transfer or external HTTP is used.
"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.events.schemas import AgentMessage
from app.integrations.fetch_ai import BusinessAgentEndpoint


async def verify():
    done = asyncio.Event()
    received = []
    with tempfile.TemporaryDirectory() as directory:
        common = dict(simulation_id="fetch-verification", seed="public-local-verification-only", inbox_path=str(Path(directory) / "inbox.db"))
        def handle(message):
            received.append(message.message_id)
            done.set()
        buyer = BusinessAgentEndpoint(agent_id="buyer", business_id="bakery", role="procurement", handler=lambda msg: None, **common)
        seller = BusinessAgentEndpoint(agent_id="seller", business_id="mill", role="sales", handler=handle, **common)
        buyer.peers[seller.address] = {"agent_id": "seller", "business_id": "mill"}
        seller.peers[buyer.address] = {"agent_id": "buyer", "business_id": "bakery"}
        @buyer.agent.on_event("startup")
        async def send(ctx):
            status = await buyer.send(ctx, seller.address, AgentMessage(message_id="verified-local-rfq", message_type="REQUEST_FOR_QUOTE", sender_id="buyer", recipient_id="seller", business_id="bakery", simulation_id="fetch-verification", payload={"item": "flour", "quantity": 10}))
            assert status.status.value == "delivered", status
        seller.agent.setup()
        buyer.agent.setup()
        await asyncio.wait_for(done.wait(), timeout=5)
        assert received == ["verified-local-rfq"]
        print(json.dumps({"status": "verified", "scope": "local_uagents_dispatch", "buyer_address": buyer.address, "seller_address": seller.address, "protocol_digest": buyer.protocol.digest, "messages_received": len(received), "agentverse_verified": False}))
        pending = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(verify())
