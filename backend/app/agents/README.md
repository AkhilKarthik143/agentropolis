# Agent roles and shared runtime

Eighteen role types run as business-owned instances inside one shared Python
runtime. They are not eighteen independent servers. `BaseBusinessAgent` provides
identity, permissions, task/message counters and scoped context; `AgentRegistry`
validates envelopes and dispatches durable messages; `financial_operations.py`
implements the operational review roles.

## Role contract

Every role has a stable agent identity, parent business, objective, permissions,
task state, structured message handling, private runtime memory, error handling and
tests. Agents may recommend or request an action, but authoritative changes happen
through the economy/finance command boundary.

| Role | Trigger and output | Forbidden authority |
| --- | --- | --- |
| Manager / CEO | Low-stock or recovery signal → scoped task assignment | Cannot directly settle or rewrite state |
| Procurement | Need → supplier RFQs and negotiation task | Cannot set supplier terms or pay |
| Supplier / Sales | RFQ/counteroffer → bounded quote, counter, or rejection | Cannot sell reserved/insufficient stock |
| Negotiation | Offers → ranked exact-term proposal | Cannot bypass treasury/risk/approval |
| Inventory / Operations | Stock/receipt → need or operational observation | Cannot oversell or fake receipt |
| Strategy / Pricing | Catalog/stock → price recommendation | Cannot silently change policy/catalog |
| Treasury | Proposal → affordability/reserve review | Cannot authorize outside policy |
| Payments | Approved due obligation → payment capability request | Cannot self-approve or retry uncertain outcome |
| Accounting | Journal/payment state → reconciliation review | Cannot inject arbitrary ledger lines |
| Accounts Payable | Receipt/invoice → payable match/hold | Cannot release unmatched invoice |
| Accounts Receivable | Delivered obligation → receivable/aging review | Cannot fabricate settlement |
| Risk / Compliance | Counterparty/proposal → risk decision | Cannot invent provider/credit data |
| Controller | Approval/exception → escalation | Cannot silently clear holds |
| Broker / Discovery | Need → eligible local supplier capabilities | No public discovery claim by default |
| Market Intelligence | Catalog/source → provenance-tagged observation | Cannot call local data live market data |
| Credit / Lending | Cash/commitments → simulated recommendation | Cannot issue real credit |
| Recovery | Shock/failure → replacement procurement request | Cannot guarantee capacity or outcome |
| Auditor / Observer | Events/ledger → read-only integrity report | Cannot remediate records |

The current concrete implementations are in `manager.py`, `inventory_agent.py`,
`procurement.py`, `supplier.py`, `negotiation.py`, `treasury.py`, `risk.py`,
`payments.py`, `accountant.py`, `broker.py`, `company_agent.py`,
`financial_operations.py`, and `registry.py`. See [agent-architecture](../../../docs/agent-architecture.md)
for detailed permissions and message lifecycle.

## LLM boundary

The gateway in `llm_gateway.py` can produce validated structured proposals with
replay/deterministic fallback, budgets and provenance. Its existence does not mean
all roles use live Claude. LLM output is constrained to a proposal and revalidated
by trusted services.
