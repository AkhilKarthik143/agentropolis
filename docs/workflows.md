# Workflows

The local demo starts paused with ten seeded businesses, one reserved coffee contract, and a pending capital-purchase approval. These are declared scenario inputs. Subsequent supplier choices are made by business agents from current quotes and policies.

## Procure to pay

1. A tick consumes configured demand and detects a buyer's low stock. The runtime avoids starting another need when a relevant negotiation or unfulfilled contract is already pending.
2. Inventory sends a need to Manager. Manager persists a task and sends it to Procurement.
3. Procurement discovers eligible local Supplier agents, applies allowlist/risk checks, persists a negotiation, and sends RFQs. An empty eligible set fails the task visibly.
4. Each supplier computes its own quote from cost, available capacity, liquidity, and lead time. The buyer negotiates by typed counteroffers, up to three rounds per supplier and a six-tick deadline. Suppliers independently accept, counter, or reject.
5. Negotiation selects a feasible offer according to the buyer objective. Treasury and Risk review it; Payments submits exact terms to the engine. The engine rechecks scope, counterparty, unit, totals, stock, commitments, reserves, and spending policy.
6. Below the approval threshold, acceptance creates a PO, reserves stock, and records an approved obligation. A large purchase waits for an exact-terms human decision before acceptance.
7. At the due tick, the local runtime invokes simulated shipping and receipt. Receipt transfers quantity/value and posts buyer AP plus seller AR/revenue/cost. Full receipt creates the invoice and three-way match. The HTTP delivery endpoint accepts an optional `{"quantity": N}` body for partial receipt; omitting it confirms the full remaining quantity.
8. An enabled Payments role lets the runtime request settlement of a fully received, matched, unheld obligation. The engine records submission, performs the mock bank transfer, and posts cash/AP/AR journals only on confirmed settlement.
9. An enabled Accounting role lets the runtime request reconciliation, which checks the provider reference and both parties' bank/ledger cash. A reconciled payment is terminal for repeated pay requests.

Signing, delivery, invoicing, payment, and reconciliation are distinct records/events even when several happen during one local tick. The mock scheduler is not an external fulfillment provider.

## Human approval

A purchase at or above the effective threshold creates `ApprovalRequested`, binds the entire pending proposal to a terms hash, and leaves stock/cash unchanged. Approval uses the local `human_operator` identity, rechecks the hash and current economic policy, then accepts or rejects. Changed terms require a new authorization. The supplied identity is not an authenticated account; this workflow is for a trusted local operator.

The seeded espresso machine illustrates this path. Approving it does not pay immediately: it enters the same reservation/receipt/match/settlement lifecycle as other contracts.

## Supplier failure and recovery

The supplier-bankruptcy or delivery-failure shock changes the selected supplier's availability, defaults its outstanding affected contracts, releases remaining reservations, cancels unpaid obligations, and emits `RecoveryRequested`. It does not choose a replacement or create free stock.

The buyer's Recovery role deduplicates the event and checks remaining alternatives. Feasible capacity triggers a new need through Manager and Procurement. New RFQs, quotes, risk checks, negotiation, and authorization determine the replacement. A recovery flag connects the new contract to the scenario; success is visible only after its real local lifecycle completes. When no alternative exists or the Manager role is unavailable, `RecoveryFailed` records that outcome.

Other shocks change the underlying condition: increased demand, a stock shortage, a reserve lock, a failure on the next simulated payment, or an invoice hold. Recovery is not guaranteed under inadequate stock, liquidity, risk policy, or a missing team role.

## Payment failures and uncertainty

A definite mock failure leaves the payment `FAILED` with no settlement journal. A later tick may retry after the condition clears. A timeout or unconfirmed external result becomes `UNCERTAIN`; repeated pay requests do not resubmit it. Provider confirmation must match authorized payer, payee, and amount before posting. External adapter journal reconciliation remains a manual investigation path and is not wired as a live operating bank in the default API.

Invoice holds block payment and are surfaced by Controller. There is no general UI workflow to clear arbitrary held invoices or to approve new bank details; do not present these as completed automated exceptions.

## Operating API

Use `/api/simulations/{id}` as the base (`demo_001` is the default). FastAPI `/docs` is the schema reference.

| Action | Method and suffix |
| --- | --- |
| Read state / agents / events | `GET /`, `GET /agents`, `GET /events?since=N` |
| Step or run clock | `POST /tick`, `/resume`, `/pause`, `/speed` with `{"speed": 1}` |
| Add / edit business | `POST /businesses`, `PATCH /businesses/{business_id}` |
| Apply disruption | `POST /shock` with `{"type":"supplier_bankruptcy","supplier_id":"northstar_roasters"}` |
| Decide approval | `POST /approvals/{approval_id}` with `{"approved":true,"approver":"human_operator"}` |
| Explicit lifecycle commands | `POST /contracts/{deal_id}/ship`, `/deliver`, `/pay` |
| Reconcile | `POST /payments/{payment_id}/reconcile` |
| Verify | `GET /audit/verify`, `GET /ledger/proof` |
| Reset local simulation | `POST /reset`; SQLite state is checkpointed first and streams resync |

The replay endpoint reports retained event history. It is not an arbitrary-time economic state reconstruction. The [demo guide](demo.md) provides the shortest reproducible route through the implemented journey.
