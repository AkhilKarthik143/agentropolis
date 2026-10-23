# Setup and external credentials

The offline application requires no external credentials.

| Service | Variables | Status |
|---|---|---|
| Claude | `CLAUDE_API_KEY`, `CLAUDE_MODEL` | Optional; fallback works offline |
| ASI:One | `ASI1_API_KEY`, `ASI1_MODEL` | Optional; not required for local demo |
| Agentverse | `AGENTVERSE_KEY`, `GATEWAY_SEED`, `GATEWAY_PORT` | Needed for external mailbox verification |
| Nessie | `NESSIE_MODE=sandbox`, `NESSIE_API_KEY` | Needed for sandbox verification |
| Coinbase x402 | `X402_MODE=testnet`, `X402_NETWORK`, `X402_WALLET_PRIVATE_KEY` | Needed for testnet verification |
| Apify | `APIFY_MODE=live`, `APIFY_API_TOKEN`, `APIFY_ACTOR_ID` | Needed for live actor data |
| SpacetimeDB | `SPACETIMEDB_URI`, `SPACETIMEDB_DATABASE` | Not adopted until a writer/subscription test passes |

Never copy credentials from AgentPlace. Put local values only in the standalone
`.env`, which is ignored by Git.
