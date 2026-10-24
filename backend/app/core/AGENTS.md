# Core coding-agent instructions

Keep settings deterministic and standalone. Add a new environment variable to
`.env.example`, `docs/USER_SETUP_REQUIRED.md`, and the relevant sponsor guide at
the same time. Use safe defaults that start the local demo without credentials.

Do not make a provider key switch the authoritative bank/payment mode implicitly.
Test relative and absolute data directories, CORS behavior, and missing/invalid
configuration. Never print environment values in tests or completion reports.
