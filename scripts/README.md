# Project scripts

Scripts are operator-facing helpers for the independent local project:

- `dev.sh` starts the FastAPI backend and Vite frontend.
- `preflight.sh` runs backend tests, isolated economy smoke, and local uAgents proof;
  it reports external sponsor gates without pretending they passed.
- `reset_demo.sh` resets only the loopback `demo_001` local simulation.
- `check_docs.py` validates required documentation and local Markdown links.

Provider verifiers live under `backend/scripts/` because they import backend
adapters. Never point these scripts at AgentPlace, a production account, or a
non-loopback reset target without explicit reviewed authorization.
