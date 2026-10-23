# Standalone architecture

The frontend runs on port 5173 and proxies `/api` and `/ws` to the independent
Agentropolis FastAPI server on port 8001.

```text
React/Vite frontend
        │ HTTP + WebSocket
        ▼
Agentropolis FastAPI (app.main)
        │
        ├── simulation/economy API
        ├── business agent runtime and local gateway
        ├── deterministic EconomyEngine
        ├── finance controls and double-entry ledger
        └── append-only hash-chained EventBus
                │
                └── SQLite in backend/.data/economy.db
```

Each buyer business owns a Manager, Inventory, Procurement, Negotiation,
Treasury, Risk, and Payments team. Supplier businesses own Supplier Agents.
The teams exchange typed messages through the in-process registry; the
message/task events are persisted in the same event store as economic events.
The full lifecycle is documented in [agent-ecosystem.md](agent-ecosystem.md).

The runtime is deliberately one worker process for the MVP. Agent roles are
independent in identity, objective, permissions, and task state, while the
economy remains centralized only at the trusted execution boundary. Agents can
propose actions, but only `EconomyEngine` can authorize and commit contracts,
payments, inventory receipts, and ledger entries.

No executable code in this project imports AgentPlace, calls an AgentPlace URL,
reads AgentPlace environment variables, or uses AgentPlace database tables.
