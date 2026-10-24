# Product scope and acceptance

Agentropolis is a standalone local economy where company-owned agents negotiate and trusted services enforce inventory, authorization and financial rules. It does not import AgentPlace or access its database/configuration.

## User journeys

1. Owner creates a buyer, supplier or broker with a cash budget, inventory, objective and allowed roles. Inspect its deployed agents and pause the company.
2. Buyer inventory detects a need. Manager/procurement request quotes. Independent suppliers compute offers using their own catalog, costs and stock. Negotiation counters for up to three rounds; risk and treasury can block. A large purchase remains pending until the local human operator approves the exact proposal.
3. Accepted purchase reserves supplier inventory. Receipt posts inventory/AP and AR/revenue/COGS independently. Only a full match and authorization permit payment. Reconciliation checks the bank record and each entity's books.
4. Operator fails a supplier. Existing eligible contracts default, reservations release, recovery agents discover current alternatives and issue a fresh procurement task. No feasible supplier produces a failure rather than a scripted replacement.
5. Operator inspects events, public reasoning, messages, tasks and financial evidence. Restart recovers SQLite economic state, messages and tasks. Reset makes a recoverable database backup.

## Delivered local boundary

Ten seeded companies span coffee, packaging, equipment, logistics and research. Buyer/supplier negotiation is implemented for catalog items; a company name alone does not imply a complete industry simulator. Eighteen role implementations share one durable runtime. Advanced strategy, credit and market intelligence currently produce deterministic recommendations/observations; they do not issue loans or autonomously change market prices.

Seven routes and the agent dialog use backend data. The default demo is paused and requires explicit ticks or Resume. Local deterministic policies are usable without keys; configured live reasoning remains unverified until an account-backed run.

## Audit and risk register

| Prior issue / risk | Current handling |
|---|---|
| Central engine impersonated suppliers and buyer | Decisions moved to company agents and typed durable messages |
| Signing could imply receipt/payment | Explicit reservation, receipt, invoice, match, payment and reconciliation states |
| Global balance could hide one-sided entries | Every entity balances separately; strict integer cents |
| Repeat command / process crash | Atomic SQLite economic commands, durable outcomes, stable idempotency and at-least-once inbox |
| Overlapping orders oversell or reuse cash | Reservations and outstanding commitments checked while serialized |
| Private notes in public events | Nested private rationale stripped before event storage/public runtime projection |
| Omitted roles can bypass controls | Missing manager blocks recovery; payment/accounting roles gate automatic steps |
| Real provider outcome uncertain | Adapter journal retains uncertainty; no automatic duplicate submission |
| UI implies external sponsor success | Explicit simulation environment and evidence matrix |
| Multi-user deployment | Not accepted: no authentication/tenant access control; local trusted operator only |

## Remaining acceptance

The complete master specification is not yet satisfied. Public agent discovery, external sandbox banking, testnet digital-service purchase with service-expense accounting, live Claude/Apify evidence, Figma artifacts, production identity/authorization and scale/fault benchmarks need further work or access. The authoritative verdict is `implementation-report.md`, with external prerequisites in `USER_SETUP_REQUIRED.md`.
