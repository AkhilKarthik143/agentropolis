# Agentropolis agent ecosystem

Agentropolis uses one worker process to host multiple business-owned agent
teams. The process is intentionally small for local development and the
hackathon demo; the message envelope and registry are transport-independent so
selected roles can later be exposed through Fetch.ai.

```text
Simulation clock
      │
      ▼
Inventory Agent ──► Manager Agent ──► Procurement Agent
                                           │
                 ┌─────────────────────────┴────────────────────────┐
                 ▼                                                  ▼
          Supplier Agents                                   Negotiation Agent
                 │                                                  │
                 └─────────────── quotes / counteroffers ───────────┘
                                           │
                              Risk Agent + Treasury Agent
                                           │
                                    Payments Agent
                                           │
                              EconomyEngine command gate
                         contract · bank · inventory · ledger
```

## P0 roles currently implemented

| Role | Business boundary | Responsibility | State-changing authority |
| --- | --- | --- | --- |
| Manager | One business | Assigns work from operating signals | None; creates tasks |
| Inventory | One business | Detects low stock and confirms receipt | Only through engine receipt command |
| Procurement | Buyer business | Requests quotes and creates typed purchase proposals | None; proposes only |
| Supplier | Supplier business | Quotes from its own capacity, price style, and reliability | None; quotes only |
| Negotiation | Buyer business | Ranks quotes and makes bounded counteroffers | None; emits decisions |
| Risk | Buyer business | Checks credit, reliability, and counterparty availability | None; can block a proposal path |
| Treasury | Buyer business | Checks cash, reserves, spend limits, and approval thresholds | None; recommends/escalates |
| Payments | Buyer business | Submits a proposal to the trusted command handler | Cannot call the bank directly |

## Message lifecycle

1. The clock invokes each buyer's Inventory Agent.
2. A low-stock signal becomes an `INVENTORY_LOW` message.
3. Manager assigns a `source_inventory` task to Procurement.
4. Procurement asks each active Supplier Agent for a quote.
5. Risk filters unreliable or CRS-blocked suppliers.
6. Negotiation selects a quote and may send a bounded counteroffer.
7. Treasury checks liquidity. Payments submits the typed proposal.
8. The `EconomyEngine` validates authorization, finance controls, approvals,
   banking, and double-entry accounting.
9. Agent proposals use `delivery_mode=on_receipt`: payment and contract
   authorization happen first; inventory changes only when the delivery
   endpoint confirms physical receipt.

Every task and message is also emitted through the hash-chained EventBus, so
the existing SQLite event store persists the operational trail alongside
financial events.

## Trusted boundary

Agents can read scoped business information and make recommendations. They
cannot grant themselves permissions, transfer money, write ledger entries,
change inventory, or finalize contracts. Those operations remain inside the
deterministic `EconomyEngine` and finance services.

Useful inspection endpoints:

```text
GET  /api/economy/agents
GET  /api/economy/agents/tasks
GET  /api/economy/agents/messages
POST /api/economy/tick
POST /api/economy/contracts/{deal_id}/deliver
```

## Later roles

Accountant, Accounts Payable, Accounts Receivable, Controller, Broker, Market
Intelligence, Credit/Lending, Recovery, Strategy/Pricing, Auditor/Observer,
and a richer CEO/Manager can be added using the same `BaseBusinessAgent`,
`AgentMessage`, `AgentTask`, and `AgentRegistry` contracts. They should be
added as real workflows, not as empty role labels or unrestricted LLM loops.
