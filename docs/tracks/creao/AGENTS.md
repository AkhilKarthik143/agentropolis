# Creao implementation-agent instructions

Mission: verify Creao's actual platform capabilities before writing integration
code, then implement one meaningful company-management workflow.

Own only a future explicit Creao adapter, its tests, setup, and this guide. Do not
invent endpoint names, SDK calls, or a sponsor claim. Coordinate with API, agents,
finance, and frontend owners for task/approval contracts.

Require scoped user/business authorization, typed requests/responses, timeouts,
retry/uncertainty handling, audit events, and no direct financial mutation. Run
local business/agent tests first; add provider tests only with official fixtures or
approved sandbox access. Acceptance requires a genuine Creao-powered workflow and
sanitized evidence. Update matrix, setup, security, final readiness, and report
exact capability blockers.
