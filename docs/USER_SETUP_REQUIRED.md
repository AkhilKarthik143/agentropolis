# Setup and external access

Updated October 23, 2026. **No API key is needed for the local demo.** Copy `.env.example` into a private, ignored `.env` and configure only the services you intend to use. Never copy AgentPlace secrets. The running economy uses its local ledger, bank and agent transport by default. Configuring an external adapter does not switch economic settlement to that adapter.

| Service | Required access | Purpose / priority | Verified implementation status | Official setup | Estimated cost |
|---|---|---|---|---|---|
| Local Python/Node/SQLite | Local dependencies | Needed immediately | Local application; no hosted database required | Repository README | No service charge |
| Anthropic | API account and `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`; `AGENTROPOLIS_LLM_MODE=live` when constructing the gateway | Optional reasoning; needed before claiming a live Claude demo | Role-specific structured SDK adapter, budget and fixture tests. No live credential-backed response verified | [API keys](https://platform.claude.com/settings/keys), [structured output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [pricing](https://platform.claude.com/docs/en/about-claude/pricing) | Default Haiku 5.5: $0.10/million input and $0.50/million output for short prompts; local reservation cap $0.10/gateway. Different models require updated rates |
| Fetch.ai / Agentverse | Private persistent seed, Agentverse account/API key, reachable HTTPS endpoint, explicit registration | Needed before claiming public agent discovery and communication | Independent identities + typed protocol exercised through real local uAgents dispatch. Public registration/discovery not verified | [Onboard a uAgent](https://docs.agentverse.ai/documentation/launch-agents/agentverse-sdk/u-agents), [search API](https://uagents.fetch.ai/docs/guides/search) | Local SDK has no hosted-service charge; public account/hosting/network costs must be checked with provider |
| Capital One Nessie | Sandbox key, explicit test address, fake customer/account mapping | Needed before a Nessie sandbox demonstration | HTTP contract fixtures, durable uncertainty/idempotency journal and balance lookup pass. No credential-backed sandbox run | [Nessie](https://api.nessieisreal.com/), [official SDK](https://github.com/nessieisreal/nessie-javascript-sdk) | Fake-money banking; current service/access terms unverified because portal returned HTTP 403 during research |
| Coinbase x402 | Optional backend x402 dependencies; approved HTTPS service URL and recipient; throwaway Base Sepolia wallet funded with test USDC | Needed before a paid digital-service testnet demo | v2 HTTP challenge/signing boundary, strict testnet/recipient/asset/cap validation, durable submission journal and RPC receipt check. Provider responses tested with HTTP fixtures; external settlement and optional signer execution not yet verified | [Buyer quickstart](https://docs.cdp.coinbase.com/x402/buyer/quickstart), [official SDK](https://github.com/coinbase/x402/tree/main/python/x402), [faucets](https://docs.cdp.coinbase.com/faucets/introduction) | Test tokens have no intended monetary value. Resource charges, facilitator fees and production costs depend on provider; production networks are refused |
| Visa Intelligent Commerce | Visa Developer account and approved product/sandbox access if API integration is chosen | Optional; shopping functionality exists independently | Product alignment only. No Visa token/payment API integration or verified sponsor eligibility | [Product / sandbox](https://developer.visa.com/capabilities/visa-intelligent-commerce/overview), [developer MCP](https://developer.visa.com/mcp-docs) | Visa lists sandbox as free; production pricing by agreement |
| Hyphenate | Actual event challenge brief; sponsor access if a private API is required | Needed before claiming track eligibility | Finance workflow alignment, no Hyphenate API integration | [Finance platform](https://hyphenate.ai/platform) | No public API price verified; contact sponsor if required |
| Apify | Token and an existing successful Actor dataset with `price_cents` or decimal `price`, optional `item`, `unit`, `url` | Optional market observations | Dataset read/normalization fixtures pass; no live account-backed dataset verified. No Actor launches | [API token](https://console.apify.com/settings/integrations), [dataset API](https://docs.apify.com/api/v2/actor-runs-last-dataset-items-get), [pricing](https://apify.com/pricing) | Free allowance/paid usage depend on plan and Actor; obtain selected Actor estimate before running it |
| CRS Credit | Official sandbox brief and test identities | Optional | Fixture only; no endpoint guessed | Obtain exact official sponsor brief | Unverified |
| SpacetimeDB | Service/account if later adopted | Optional | Not connected; SQLite and WebSocket remain authoritative | [Docs](https://spacetimedb.com/docs/) | No current dependency; hosting costs depend on plan |
| Paper / Figma | Connected design MCP account and file access | Design authoring only, not runtime | See root design verification report for actual artifacts | [Paper](https://paper.design/), [Figma](https://www.figma.com/) | Existing account plan; no runtime charge in this project |
| Microsoft | Event brief; Azure access only if actually required | Optional track | No Azure dependency or Microsoft API integration | [Azure](https://azure.microsoft.com/) | $0 current Azure use; optional deployment costs vary |
| Deployment/domain | Chosen host, TLS and optional domain | Optional for public demo | Local deployment is sufficient; no cloud service purchased | Choose provider after local verification | Provider/domain dependent; not estimated without deployment size |
| Hackathon registration | Exact event page, rules, deadline, team registration and sponsor submission requirements | Needed before submission | Requested sponsor list comes from supplied specification; official event-specific requirements and eligibility are not verified | Obtain official event/Devpost link | Registration/prize rules unknown |

## Verification commands

Run from `backend/` with its dependencies installed:

```sh
python3 -m pytest tests/test_external_adapters.py tests/test_llm_gateway.py tests/test_transport_fetch.py tests/test_sponsor_controls.py
python3 scripts/verify_fetch.py
python3 scripts/verify_nessie.py
python3 scripts/verify_x402.py --max-cents 1
```

The last two exit `2` with `NOT VERIFIED` when configuration is absent. Nessie defaults to account/history reads. x402 defaults to reading a payment challenge; this does not verify a payment. Variables must be exported into the script environment; these scripts do not silently load a different project's `.env`.

An operator may explicitly run `verify_nessie.py --execute-sandbox` to create fake test customers/accounts and submit a one-cent fake transfer. Nessie responses may remain pending: submission is not completion. Do not repeat a setup run after a timeout without checking the provider records.

For an independently approved x402 testnet test, install `python3 -m pip install -e '.[x402]'`, configure only Base Sepolia, then use `verify_x402.py --execute-testnet --max-cents 1 --authorization-id UNIQUE_APPROVAL_ID`. Keep the same authorization ID if investigating uncertainty; the durable journal refuses repeat submission. Never delete the journal to force a retry. No live/testnet payment was executed during this build.

Preserve `.data/nessie-submissions.sqlite3` and `.data/x402-submissions.sqlite3` across restarts. They are security state, not disposable caches. Uncertain submissions currently require manual provider investigation; automatic reconciliation of those adapter journals is not implemented.

## Remaining external acceptance evidence

Before describing an integration as externally verified, capture a sanitized provider request/reference, response status, time, account/network mode, and resulting event/ledger reconciliation where applicable. A missing key must never be replaced with a successful fixture indicator. Public Fetch requires a real registered reachable endpoint and a separate agent/network exchange; the local verification command does not satisfy this claim.
