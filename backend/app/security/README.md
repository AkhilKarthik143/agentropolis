# Security gates

`app/security/gate.py` centralizes the mutating capability tokens used by the
trusted local operator API. This is a local-demo guard, not a complete identity,
tenant, or production authorization system. Provider configuration and payment
rails must fail closed when safety conditions are absent.

Security documentation is in `docs/security.md` and required human setup is in
`docs/USER_SETUP_REQUIRED.md`. Keep `.env` ignored, use sandbox/testnet accounts,
cap provider actions, and never expose private keys to the frontend.
