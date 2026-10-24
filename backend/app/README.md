# Backend application packages

This package contains the standalone Agentropolis service. Its major boundaries are
API projection (`api`), role behavior (`agents`), configuration (`core`), schema
and stores (`database`), authoritative economic state (`economy`), events (`events`),
financial controls (`finance`), provider seams (`integrations`), orchestration
(`orchestration`), and local security gates (`security`).

The package does not import AgentPlace or depend on a second application server.
Read the child README and `AGENTS.md` before changing a boundary. The backend
entrypoint is `main.py`; the local health endpoint is `/health`.
