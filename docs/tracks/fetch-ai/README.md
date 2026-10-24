# Fetch.ai — agent discovery and communication

## Goal and product fit

Fetch.ai provides a natural protocol for discovering business-owned agents and
exchanging typed RFQs, quotes, counteroffers, acceptances, and expirations. The
repository intentionally distinguishes local in-process transport, local uAgents
dispatch, and public Agentverse reachability.

## Architecture and agents

`backend/app/integrations/fetch_ai.py` and `backend/app/agents/transport.py` use
stable identities, typed envelopes, peer checks, and durable inbound handling.
Broker, Procurement, Supplier, Negotiation, and Manager participate. The local
authoritative queue remains responsible for session/business permissions and
economic effects.

## Current and missing functionality

`backend/scripts/verify_fetch.py` passes a real local uAgents exchange between
distinct addresses. It explicitly reports `agentverse_verified=false`. Missing are
public registration, reachable endpoint, discovery, and external exchange evidence.
Required variables include `AGENTVERSE_KEY`, `FETCH_AGENT_SEED`, and
`FETCH_PUBLIC_ENDPOINT` as applicable to the selected deployment.

## Test and demo

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_transport_fetch.py
tests/test_external_adapters.py)` and `python3 backend/scripts/verify_fetch.py`.
The final demo must show supplier discovery and a multi-round negotiation with
correlation, retries/expiry, and no spoofed sender; public claims require public
evidence.

## Definition of done

Useful economic messages genuinely traverse the supported Fetch.ai system, are
bound to the correct business/session, and produce an audited local result.
