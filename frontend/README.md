# Agentropolis frontend

The frontend is a React/TypeScript/Vite dashboard that visualizes authoritative
backend state. Main routes are the living world, businesses/detail, negotiation
room, procurement, control tower, and scenario lab. `src/lib/economy-api.ts` calls
the API; `src/hooks/useEconomyEvents.ts` consumes WebSocket events; the economy
components render businesses, agents, relationships, controls, and motion.

Run from the repository root with `./scripts/dev.sh`, or from `frontend/` with the
existing npm scripts. The backend must be available at the configured proxy/API
origin. Install with `npm ci`; build and lint with `npm run build` and `npm run lint`.
Browser tests are under `frontend/tests/` and use Playwright configuration in
`playwright.config.ts`.

The UI is a projection, not an economic authority. It must not invent a payment,
receipt, approval, or supplier result for an animation. Current frontend source is
under concurrent redesign ownership; the final build/browser acceptance is pending
that handoff. See [final readiness](../docs/final-readiness.md).
