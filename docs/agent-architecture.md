# Agent architecture

Eighteen role types share `BaseBusinessAgent`, `AgentContext`, `AgentRegistry`, and `RuntimeStore`. Identities are stable per role and business; queue and state keys also include the simulation. Buyers and suppliers choose independently within their policies. A single local worker hosts them; they are not eighteen separately deployed services or eighteen live LLM agents.

Buyer teams receive Manager, Inventory, Procurement, Negotiation, Treasury, Risk, and Payments roles. Suppliers receive Supplier. All business kinds receive the operational review roles below, except Recovery, which belongs to buyers. An empty `agent_roles` configuration selects the default team; a nonempty list restricts it. Core autonomous procurement needs the full buyer chain and at least one active supplier with a Supplier role. Disabling a required role can block its dependent workflow.

## Role matrix

| Role | Implemented behavior and state | Authority / present limit |
| --- | --- | --- |
| Manager | Converts low-stock or recovery signals into stable `source_inventory` tasks; retains last task/action result | Assigns tasks; no general executive planning loop |
| Inventory | Detects low stock and publishes quantity needs; runtime suppresses duplicate open needs | Reads stock and publishes needs; due receipts are simulated by the runtime through engine commands |
| Procurement | Discovers candidates, applies buyer allowlist and risk checks, persists negotiation session, sends one RFQ per candidate | Requests quotes; does not set seller prices or reserve stock |
| Supplier | Quotes from its own catalog, cost floor, unreserved inventory, liquidity, and lead time; caches each round's decision in private runtime memory | Accepts, counters, or rejects bounded offers; no live external sales agent |
| Negotiation | Tracks separate supplier replies, up to three rounds and a six-tick deadline; ranks viable offers by buyer objective | Proposes exact terms; live/record mode can use validated Claude comparison and counteroffer decisions |
| Treasury | Reviews spend and reserve policy; escalates large purchases | Recommendation only; engine rechecks committed cash and final thresholds |
| Risk | Checks availability, seeded credit status, reliability, and suspicious supplier instructions | Blocks counterparties; live credit underwriting is absent |
| Payments | Accepts the Treasury/Risk proposal path and submits through a scoped capability; runtime pays due matched obligations when this role is enabled | Cannot call bank from a message handler; engine controls settlement |
| Accounting | Compares bank cash to entity ledger and verifies entity journals; enabled role allows runtime reconciliation of confirmed payments | Review and trusted reconciliation command; journals are posted by economic commands |
| Accounts Payable | Lists outstanding obligations and receipt/hold eligibility | Reviews invoices; engine matching and payment remain authoritative |
| Accounts Receivable | Reports receivables, outstanding delivered contracts, and simple overdue aging | No external collections messages or fee enforcement |
| Controller | Surfaces pending approvals, invoice holds, and uncertain payments | Escalates for operator attention; does not resolve holds automatically |
| Broker | Discovers active local suppliers and available item capabilities; supports procurement discovery | Local registry only; no public network routing in this workflow |
| Recovery | Deduplicates disruption events, checks alternatives, and requests a new procurement workflow; records failure when no capacity exists or Manager is unavailable | Coordinates fresh negotiation; no hardcoded winning supplier or guaranteed success |
| Strategy | Recommends catalog prices using cost floor and remaining stock | Recommendation only; does not silently change prices |
| Market Intelligence | Records source-tagged observations of local supplier catalogs | Explicit simulation provenance; no automatic live Apify refresh |
| Credit | Reports cash, commitments, and a conservative simulated financing recommendation | Issues no loan, real credit decision, or synthetic funding |
| Auditor | Checks event chain, entity balance, settlement-before-receipt anomalies, and missing authorizations | Read-only observation; no remediation or external audit certification |

The final ten roles use policy branches in `financial_operations.py`. They persist their last review and emit `AgentReviewCompleted` when results change. These are concrete deterministic operations, with narrower autonomy than the core negotiated procurement workflow. The LLM gateway supplies additional structured interfaces, but their presence is not evidence that every role invokes them. The default runtime uses deterministic policy; credential-backed Claude execution remains unverified.

## Messages and task lifecycle

Messages carry typed kind, sender, recipient, business, simulation, correlation, schema version, payload, and idempotency key. The queue uses simulation ticks for availability/expiry. Default TTL is 12 ticks; delivery claims use a 30-second wall-clock lease. A failed handler retries after increasing tick delays and becomes a dead letter after three attempts. A crashed worker's expired lease can be reclaimed. Acknowledgement means the handler returned, not that a contract or payment succeeded.

Tasks persist assignment, workflow payload, status, and outcome. The procurement path moves through queued/running/waiting and then completed or failed; human approval can leave work waiting. Negotiation state stores expected suppliers, independent offers, completed suppliers, per-supplier rounds, budget, deadline, selected proposal, and reason. The store preserves agent counters and per-agent policy memory across restarts.

Handlers persist stable decisions and reuse deterministic outbox keys so redelivery cannot create a different response for an already decided supplier round. Queue writes, memory writes, and economic writes remain separate transactions. This is at-least-once processing with idempotent effects, not a claim of end-to-end exactly-once distributed execution.

## Permission boundary

Registration captures immutable permission sets in the registry. Dispatch validates sender/recipient roles, business ownership, session, and allowed message kind; it repeats validation when recovering persisted work. Cross-business messages are restricted to RFQs, quotes, and counteroffers. During a handler, an active-agent identity prevents another role's capability or private-memory namespace from being used through `AgentContext`.

The engine independently validates economic proposals. The normal flow is Negotiation → Treasury/Risk → Payments → engine. Agents cannot grant their own approvals or write arbitrary journal lines through these capabilities. Python agents still share a process and receive application context: this is a code-level trust convention, not an OS sandbox for hostile plug-ins. The local operator API also lacks authenticated multiuser isolation.

## Execution and inspection

Each tick advances demand/clock, drains messages, processes recovery events, fulfills due simulated contracts, pays eligible obligations, runs operational reviews, expires negotiations, and detects new needs. Bank settlement and physical delivery are explicit simulation actions in this mode. They are not evidence of goods delivery or payment outside the application.

Inspect `/api/simulations/{id}/agents` for agents, tasks, messages, negotiations, transport mode, and reasoning usage. Default-world compatibility routes include `/api/economy/agents/tasks` and `/api/economy/agents/messages`. The dashboard's agent inspector exposes work and permissions; events provide the causal public trail.

The Fetch adapter separately supports stable uAgents identities, typed messages, peer checks, and durable inbound handling. Its local verification does not replace the authoritative local queue or establish public Agentverse discovery. [Sponsor status](sponsor-matrix.md) records the exact evidence and remaining integration work.
