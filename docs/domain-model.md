# Domain model

All economic amounts use integer USD cents. Quantities use whole units with an explicit catalog unit. Positive ledger values are debits and negative values are credits. Each entity's journal entry must balance independently; a buyer imbalance cannot be hidden by an opposite seller imbalance.

| Record | Meaning and principal fields |
| --- | --- |
| Simulation | Session ID, seeded flag, clock, pause/speed, faults; owns isolated economic and runtime records |
| Business | Identity/type/role, objective, activity, inventory/catalog, account, reserves, spending/approval limits, required reliability, allowlist, selected agent roles |
| Inventory | On-hand quantity per item plus reservation records; available = on-hand minus outstanding reservations |
| Agent | Business-owned role identity, registered permissions, counters, status, task reference |
| Agent task/message | Durable work assignment or typed communication with simulation/correlation/idempotency scope |
| Negotiation | Buyer need, budget/deadline, supplier participants, independent offers, rounds, conclusion, optional recovery flag |
| Proposal | Exact buyer/seller/item/unit/quantity/price/delivery terms, rationale, session, proposing identity, idempotency key |
| Approval | Decision for an exact pending proposal, including a hash of its complete serialized terms |
| Contract | Parties and accepted terms, reservation, due tick, delivered quantity, fulfillment/payment state, control-record IDs, authorization hash |
| Purchase order | Approved item, quantity, price, total, terms, cost center, distinct duty identities |
| Goods receipt | PO and total quantity confirmed upon full receipt; partial delivery quantities are also recorded in events/journals |
| Supplier invoice | Supplier-scoped invoice number, PO, amount, due date, terms, tax, cost center |
| Three-way match | PO/receipt/invoice identities and checks for supplier, amount, PO reference, and received quantity |
| Payment | Obligation, payer/payee, amount/currency/rail, authorization hash, idempotency key, submission attempts, provider reference, reconciliation state |
| Journal entry | Stable entry ID, entity, balanced lines, memo, idempotency key |
| Event | Ordered sequence, session/business/deal correlation, type/payload, idempotency key, previous hash and hash |

## Separate state dimensions

Fulfillment proceeds through `RESERVED`, `SHIPPED`, `PARTIALLY_RECEIVED`, and `RECEIVED`; disruption can default an outstanding contract. Payment proceeds through `APPROVED`, `SUBMITTED`, `CONFIRMED`, and `RECONCILED`, with `FAILED`, `UNCERTAIN`, and `CANCELLED` outcomes. The contract also carries a legacy status/state projection for UI compatibility. Use fulfillment and payment fields when deciding whether inventory or cash moved.

`APPROVED` on a payment record means an authorized obligation exists. It does not mean a provider accepted or settled a transfer. A partial receipt cannot release payment. `UNCERTAIN` is retained without automatic resubmission until positive provider investigation resolves it.

## Economic postings

Signing a contract creates its PO, reserves supplier stock, and counts the full unpaid obligation against the buyer's available commitment capacity. It does not move cash or book a receipt.

At goods receipt, the buyer debits Inventory and credits Accounts Payable at purchase price. The seller debits Accounts Receivable and credits Revenue, then debits Cost of Goods Sold and credits Inventory at its carrying value. Each partial delivery posts only the received amount; the final delivery creates the full receipt/invoice match. For catalog entries marked `service`, the buyer posts Service Expense instead of inventory; the standalone x402 adapter is not yet wired into this economic service path.

At confirmed payment, the buyer debits Accounts Payable and credits Cash; the seller debits Cash and credits Accounts Receivable. Reconciliation checks the recorded bank transaction and each party's bank cash against ledger cash. Inventory consumption reduces the item's carrying value and posts expense through engine commands.

Initial cash and stock are balanced against opening equity. Seed catalog values and credit scores are simulation fixtures. Source provenance distinguishes local catalog observations from optional external intelligence; a scraped price would not prove current supplier inventory.

## Persistence and identifiers

Economic snapshots and their command events commit atomically. Queue/task/memory records commit separately with session-scoped keys. Contract, reservation, invoice, payment, and journal IDs connect the lifecycle; stable keys return prior outcomes on repeated commands. [Workflows](workflows.md) describes how these records are created and [security](security.md) describes the limits of their trust boundary.
