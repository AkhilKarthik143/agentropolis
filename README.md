# Agentropolis

Agentropolis is a standalone autonomous-economy simulation. It owns its
FastAPI server, React frontend, SQLite event store, migrations, configuration,
agent runtime, integration adapters, tests, and deployment files.

AgentPlace is not required, imported, mounted, or accessed at runtime. The
earlier project was used only as read-only inspiration during extraction.

## Start independently

```bash
cd agentropolis
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e './backend[test]'

# terminal 1
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# terminal 2
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173/economy/world>. The backend health check is
<http://127.0.0.1:8001/health>.

## Validation

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm run build
cd .. && backend/scripts/demo_smoke.sh --full
```

The offline demo uses SQLite, deterministic seed data, mock banking, fixture
supplier intelligence, and a local Chat Protocol-shaped gateway. External
credentials are optional and are never copied from another project.

## Project layout

```text
agentropolis/
├── backend/app/       FastAPI app, economy, business agents, finance, integrations
├── backend/tests/     backend tests
├── backend/migrations/SQLite migrations
├── frontend/          standalone React/Vite app
├── infra/              Docker and deployment definitions
├── docs/               architecture, migration, setup, sponsor status
└── .env.example        Agentropolis-only configuration
```

The current autonomous team lifecycle is documented in
[`docs/agent-ecosystem.md`](docs/agent-ecosystem.md). It includes independent
buyer and supplier roles, typed task/message events, deferred delivery, and a
trusted deterministic execution boundary.
