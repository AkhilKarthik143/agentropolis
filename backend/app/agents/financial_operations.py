"""Operational financial/market roles built on the same scoped agent runtime.

These policies are deterministic and disclosed. They inspect current records and
invoke only trusted commands; they never fabricate external market or credit data.
"""

from __future__ import annotations
from dataclasses import asdict
from app.agents.base import BaseBusinessAgent
from app.events.schemas import AgentMessageType
from app.finance.ledger import Account
from app.finance.reconciliation import reconcile_business

POLICIES = {
    "accounting": ("Reconcile cash and verify entity journals", ("review_books",)),
    "accounts_payable": (
        "Match receipts and invoices before releasing obligations",
        ("review_invoices",),
    ),
    "accounts_receivable": (
        "Track customer balances and payment aging",
        ("read_receivables",),
    ),
    "controller": (
        "Escalate unresolved financial controls to the operator",
        ("review_exceptions",),
    ),
    "broker": (
        "Discover available capabilities and suppliers",
        ("discover_suppliers",),
    ),
    "recovery": (
        "Coordinate feasible alternatives after disruptions",
        ("coordinate_recovery",),
    ),
    "strategy": (
        "Recommend prices from cost, stock and observed demand",
        ("recommend_strategy",),
    ),
    "market_intelligence": (
        "Report sourced local offers with provenance",
        ("read_market",),
    ),
    "credit": (
        "Assess simulated affordability without issuing real credit",
        ("assess_simulated_credit",),
    ),
    "auditor": (
        "Inspect authorization, entity balance and event integrity",
        ("audit_records",),
    ),
}


class OperationsAgent(BaseBusinessAgent):
    def __init__(self, *, business_id, role):
        self.role = role
        objective, permissions = POLICIES[role]
        super().__init__(
            business_id=business_id, objective=objective, permissions=permissions
        )

    def discover(self, item, context):
        return [
            agent
            for agent in context.registry.for_businesses_by_role("supplier")
            if context.engine.businesses[agent.business_id].active
            and item in context.engine.businesses[agent.business_id].categories
        ]

    def inspect(self, context):
        e = context.engine
        b = e.businesses[self.business_id]
        context.require(self.agent_id, self.permissions[0], self.business_id)
        contracts = [
            c
            for c in e.contracts.values()
            if self.business_id in {c.buyer_id, c.supplier_id}
        ]
        if self.role == "accounting":
            result = {
                **asdict(
                    reconcile_business(self.business_id, b.account_id, e.ledger, e.bank)
                ),
                "entity_balanced": e.ledger.is_balanced(self.business_id),
            }
        elif self.role == "accounts_payable":
            obligations = [
                {
                    "contract_id": c.contract_id,
                    "amount_cents": c.total_cents,
                    "eligible": c.fulfillment_state == "RECEIVED"
                    and c.payment_state in {"APPROVED", "FAILED"}
                    and not e.faults.get(f"invoice:{c.contract_id}"),
                    "reason": "verified receipt required; invoice holds block payment",
                }
                for c in contracts
                if c.buyer_id == self.business_id
                and c.payment_state not in {"CONFIRMED", "RECONCILED", "CANCELLED"}
            ]
            result = {
                "obligations": obligations,
                "payable_cents": -e.ledger.balance(
                    self.business_id, Account.ACCOUNTS_PAYABLE
                ),
            }
        elif self.role == "accounts_receivable":
            result = {
                "receivable_cents": e.ledger.balance(
                    self.business_id, Account.ACCOUNTS_RECEIVABLE
                ),
                "outstanding_contracts": [
                    c.contract_id
                    for c in contracts
                    if c.supplier_id == self.business_id
                    and c.delivered_quantity
                    and c.payment_state not in {"CONFIRMED", "RECONCILED"}
                ],
                "overdue_contracts": [
                    c.contract_id
                    for c in contracts
                    if c.supplier_id == self.business_id
                    and c.delivered_quantity
                    and c.payment_state not in {"CONFIRMED", "RECONCILED"}
                    and e.clock.tick > c.due_tick + 7
                ],
            }
        elif self.role == "controller":
            result = {
                "pending_approvals": [
                    r.approval_id for r in e.approvals.pending(self.business_id)
                ],
                "invoice_holds": [
                    c.contract_id
                    for c in contracts
                    if e.faults.get(f"invoice:{c.contract_id}")
                ],
                "uncertain_payments": [
                    c.payment_id for c in contracts if c.payment_state == "UNCERTAIN"
                ],
                "human_required": True,
            }
        elif self.role == "broker":
            result = {
                "suppliers": [
                    {
                        "business_id": s.business_id,
                        "items": [
                            item
                            for item in s.categories
                            if s.inventory.available(item) > 0
                        ],
                    }
                    for s in e.businesses.values()
                    if s.active and s.role == "supplier"
                ],
                "transport": "local_registry",
                "network_verified": False,
            }
        elif self.role == "strategy":
            result = {
                "recommendations": [
                    {
                        "item": item,
                        "unit_price_cents": max(
                            int(product.get("cost_price_cents", 0)) * 110 // 100,
                            int(product.get("unit_price_cents", 0))
                            * (110 if b.inventory.available(item) < 10 else 100)
                            // 100,
                        ),
                        "reason": "cost floor and available stock",
                        "requires_policy_change": True,
                    }
                    for item, product in b.catalog.items()
                ]
            }
        elif self.role == "market_intelligence":
            result = {
                "source": "local supplier catalog observations",
                "mode": "simulation",
                "observed_tick": e.clock.tick,
                "observations": [
                    {
                        "supplier_id": s.business_id,
                        "item": item,
                        "unit_price_cents": p.get("unit_price_cents"),
                        "unit": p.get("unit"),
                        "provenance": f"local://{e.session_id}/{s.business_id}/catalog",
                    }
                    for s in e.businesses.values()
                    if s.active
                    for item, p in s.catalog.items()
                ],
            }
        elif self.role == "credit":
            cash = e.ledger.balance(self.business_id, Account.CASH)
            result = {
                "mode": "simulation_only",
                "cash_cents": cash,
                "committed_cents": e.committed_cents(self.business_id),
                "recommendation": "decline financing: no verified repayment cash flow"
                if cash - e.committed_cents(self.business_id) <= b.reserve_cents
                else "no financing needed",
                "loan_issued": False,
            }
        elif self.role == "auditor":
            result = {
                "event_chain_valid": e.audit_verification()["valid"],
                "entity_balanced": e.ledger.is_balanced(self.business_id),
                "unreceived_settlements": [
                    c.contract_id
                    for c in contracts
                    if c.payment_state in {"CONFIRMED", "RECONCILED"}
                    and c.fulfillment_state != "RECEIVED"
                ],
                "missing_authorizations": [
                    c.contract_id for c in contracts if not c.approved_terms_hash
                ],
                "records_mutated": False,
            }
        else:
            return
        previous = context.recall(self.agent_id, "last_review")
        if previous != result:
            context.remember(self.agent_id, "last_review", result)
            self.decisions += 1
            context.emit(
                "AgentReviewCompleted",
                business_id=self.business_id,
                payload={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "result": result,
                    "reasoning_mode": "deterministic_policy",
                },
            )

    def recover(self, context, event):
        context.require(self.agent_id, "coordinate_recovery", self.business_id)
        key = f"recovery:{event.seq}"
        if context.recall(self.agent_id, key):
            return
        e = context.engine
        data = event.payload
        alternatives = [
            b.business_id
            for b in e.businesses.values()
            if b.role == "supplier"
            and b.active
            and b.business_id != data.get("failed_supplier")
            and b.inventory.available(data.get("item", "")) >= data.get("quantity", 1)
        ]
        manager = context.registry.by_role(self.business_id, "manager")
        result = {
            "source_event_seq": event.seq,
            "alternatives": alternatives,
            "status": "negotiating" if alternatives else "no_feasible_supplier",
            "item": data.get("item"),
        }
        if alternatives and manager is None:
            result.update(status="blocked", reason="manager_agent_unavailable")
        context.emit(
            "RecoveryPlanProposed",
            business_id=self.business_id,
            deal_id=event.deal_id,
            payload={"agent_id": self.agent_id, **result},
        )
        if alternatives and manager is not None:
            context.send(
                message_type=AgentMessageType.INVENTORY_LOW,
                sender_id=self.agent_id,
                recipient_id=manager.agent_id,
                business_id=self.business_id,
                correlation_id=f"recovery:{event.seq}",
                idempotency_key=key,
                payload={
                    "item": data["item"],
                    "required_quantity": data.get("quantity", 12),
                    "recovery": True,
                    "failed_supplier": data.get("failed_supplier"),
                    "trigger": "economic_disruption",
                },
            )
        else:
            context.emit(
                "RecoveryFailed",
                business_id=self.business_id,
                deal_id=event.deal_id,
                payload=result,
            )
        context.remember(self.agent_id, key, result)
