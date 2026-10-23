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
        ├── local agent gateway
        ├── deterministic EconomyEngine
        ├── finance controls and double-entry ledger
        └── append-only hash-chained EventBus
                │
                └── SQLite in backend/.data/economy.db
```

No executable code in this project imports AgentPlace, calls an AgentPlace URL,
reads AgentPlace environment variables, or uses AgentPlace database tables.
