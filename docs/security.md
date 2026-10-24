# Security and trust boundaries

Agentropolis is a trusted local-operator simulation. The development launcher and Compose ports bind to loopback. The API has no login, tenant membership checks, authenticated human approver, CSRF protection, or production rate limits. Session IDs separate data; they are not access-control credentials. Do not expose the current API as a public multiuser financial service.

## Implemented controls

| Boundary | Controls in the local application |
| --- | --- |
| Agent messages | Registered sender/recipient identities, message-kind permissions, simulation and business scope checks, restricted cross-business negotiation traffic, expiring messages |
| Agent tools | Captured registration permissions, active-handler identity, scoped task assignment and memory access through `AgentContext` |
| Proposals | Typed monetary fields, exact totals/units, supported role/business/session, active and permitted counterparty, reliability/fixture credit checks, supplier stock and cost floor |
| Spending | Existing commitments deducted from available cash, reserve and spend limits, exact-terms approval hash, current policy revalidation |
| Payment | Full receipt and three-way match, invoice hold, exact payer/payee/amount authorization, durable idempotency, submitted/failed/uncertain/confirmed distinction |
| Accounting | Integer-cent lines, independently balanced entity entries, stable journal IDs, inventory reservations/carrying values, bank/ledger reconciliation |
| Persistence | SQLite serialized economic transactions, rollback, atomic snapshot/event writes, durable message retries, recoverable local reset checkpoints |
| Audit | Ordered hash-linked events and verification, public proposal rationale projection, explicit fixture/transport mode |

Private supplier notes are treated as untrusted data. A deterministic proposal gate detects tested prompt-injection patterns, and structured LLM results are constrained by schema, known candidate IDs, price bounds, and budgets. Pattern detection is not a complete prompt-injection defense; trusted economic validation remains required regardless of model output.

## What these controls do not prove

The agent runtime shares a Python process and application state. It is not a sandbox for hostile Python plug-ins, and internal identity checks do not replace authentication of an external caller. `human_operator` is a required local workflow label, not proof of the requester's identity. The local API can inspect business state, tasks, and messages; there is no confidentiality boundary between separate human tenants. Public events and runtime snapshots recursively omit `private_rationale`. Other operational message/task and business records remain available to the trusted operator; this field redaction is not a complete public-data policy.

Hash chains detect changed retained records when checked against their chain, but there is no external anchor or independent immutable log. A database administrator can rewrite data and recompute hashes. The database is not encrypted. Queue acknowledgement and command commits are separate; the processing guarantee is at least once, with idempotent economic effects rather than universal exactly-once execution.

Recovery and approval controls prevent tested invalid local effects; they do not certify real goods, provider settlement, creditworthiness, or regulatory compliance. Provider credentials and external network behavior have not been live-verified in this build. See [sponsor matrix](sponsor-matrix.md).

## Secrets and external adapters

Keep secrets in the project's ignored `.env` or an appropriate external secret store. Do not copy credentials from unrelated projects, place private keys in frontend variables, or publish `.data` files. The default `.env.example` contains empty credential fields and simulation settings.

Nessie and x402 have durable submission journals. Preserve those files across restarts; an uncertain request must be investigated using its existing authorization/idempotency reference. Deleting a journal to retry could duplicate an external effect. The x402 boundary refuses production networks and applies recipient, origin, asset, and spending constraints before signing. It is a separate optional testnet adapter, not the default goods-payment rail.

The optional LLM gateway has bounded calls/tokens/cost reservations and validates structured output. Live reasoning sends selected business context to the configured provider and incurs provider billing. No model response can directly authorize a bank transfer or arbitrary journal entry through the normal agent workflow.

## Before public deployment

Add authenticated users and server-derived approver identities; authorize every session/business read and mutation; establish tenant isolation and data retention; introduce secure secret management, TLS, request limits, and audited operator access. Complete provider reconciliation and failure recovery against actual sandbox contracts. A distributed deployment also needs scheduler ownership and a cross-process event transport. These are explicit remaining engineering tasks, not features provided by the current local demo.
