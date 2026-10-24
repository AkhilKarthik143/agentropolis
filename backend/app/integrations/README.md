# Sponsor and provider adapters

Integrations isolate optional external technology from the local economy. Current
adapters are `fetch_ai.py`, `nessie.py`, `coinbase_x402.py`, `crs_credit.py`, and
`apify.py`; Claude is implemented through `app/agents/llm_gateway.py`. There is no
verified Solana, Creao, or SpacetimeDB provider implementation in this checkout.

Each adapter must validate configuration, use typed requests/responses, set
timeouts, classify errors and uncertainty, protect idempotency, and expose enough
sanitized audit metadata for reconciliation. Fixture tests are required and live
verification must be opt-in. The default economy continues to use local transport,
mock banking, deterministic/replay reasoning, and simulated settlement.

Run `tests/test_external_adapters.py`, `tests/test_llm_gateway.py`,
`tests/test_transport_fetch.py`, and the provider scripts under `backend/scripts/`.
See [track guides](../../../docs/tracks/README.md) for credential and demo gates.
