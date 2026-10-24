# Frontend coding-agent instructions

Respect the backend API/event contracts and the active ownership boundary. Before
editing, inspect Git status and coordinate if another agent owns `frontend/src`,
`frontend/tests`, or the frontend config. Do not modify backend economic rules from
a UI task without an explicit handoff.

Use accessible semantic controls, responsive layouts, reduced-motion support, and
real API/WebSocket state. Keep loading, error, reset, disconnected, pending,
uncertain, and empty states visible. Animation must follow backend events and must
not fake financial success. Keep provider secrets out of browser code.

Run `npm run lint`, `npm run build`, and the relevant Playwright cases after a UI
change. Report viewport/browser, backend seed/reset state, exact results, screenshots
and any failed route. Update `DESIGN.md` or frontend documentation when the visual
system/API contract changes.
