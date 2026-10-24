# Application-package agent instructions

Treat each child package as a contract boundary. Keep provider code in
`integrations`, authoritative transitions in economy/finance, durable concerns in
database/events/orchestration, and HTTP projection in `api`. Do not solve a
cross-boundary problem by importing implementation details into a role or route.

Inspect child instructions and existing tests before editing. Preserve the local
startup path and run the full backend suite for shared contracts. Report any API,
event, migration, seed, or frontend coordination impact.
