# Integration coding-agent instructions

- Do not let an API key silently switch local mode or authorize an unbounded action.
- Keep provider request construction out of agent roles and economy domain objects.
- Validate origin, recipient, network, amount, currency, account, and capability
  before signing or submitting.
- Persist idempotency/submission state before external effects and preserve
  `UNCERTAIN` outcomes for human/provider reconciliation.
- Use fixture/replay tests without network access; add a separately named external
  verification command that fails closed when credentials are absent.
- Update `.env.example`, `docs/USER_SETUP_REQUIRED.md`, the relevant track guide,
  and `docs/sponsor-matrix.md` with actual status.

Never paste credentials into logs, tests, commits, or final reports. The completion
report must name the exact provider call and whether it truly succeeded.
