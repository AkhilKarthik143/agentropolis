# API coding-agent instructions

- Keep route handlers thin: parse input, select a simulation, call a trusted
  engine/service command, and translate expected domain errors into HTTP errors.
- Validate path/session/business ownership at the server; never trust a business or
  agent identifier supplied by the browser.
- Preserve the distinction between projections and mutations. Add a new mutation
  only with idempotency, audit/event behavior, and a focused guard test.
- WebSocket changes must preserve cursor ordering, reset notifications, session
  isolation, and reconnect catch-up.
- Never expose private agent memory, provider secrets, wallet keys, or raw internal
  exception details.

Run `(cd backend && PYTHONPATH=. python3 -m pytest -q tests/test_api_guards.py
tests/test_replay.py)` plus relevant engine tests. Report API examples and any
frontend coordination needed.
