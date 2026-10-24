"""Shared durable runtime: agents decide; trusted engine commands execute."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext
from app.agents.financial_operations import OperationsAgent, POLICIES
from app.agents.inventory_agent import InventoryAgent
from app.agents.manager import ManagerAgent
from app.agents.negotiation import NegotiationAgent
from app.agents.payments import PaymentsAgent
from app.agents.procurement import ProcurementAgent
from app.agents.registry import AgentRegistry
from app.agents.risk import RiskAgent
from app.agents.supplier import SupplierAgent
from app.agents.treasury import TreasuryAgent


class AgentRuntime:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.registry = AgentRegistry(engine)
        self.store = self.registry.store
        self._register_teams()

    def _register_teams(self) -> None:
        for business in self.engine.businesses.values():
            self.register_business(business)

    def register_business(self, business: Any) -> None:
        for agent_id, agent in list(self.registry.agents.items()):
            if agent.business_id != business.business_id:
                continue
            if business.agent_roles and agent.role not in business.agent_roles:
                self.registry.agents.pop(agent_id)
                self.registry._permissions.pop(agent_id, None)
            elif agent.role in {"manager", "procurement", "negotiation", "inventory"}:
                agent.objective = business.objective
        if business.role == "buyer":
            for agent in (
                ManagerAgent(
                    business_id=business.business_id, objective=business.objective
                ),
                InventoryAgent(
                    business_id=business.business_id, objective=business.objective
                ),
                ProcurementAgent(
                    business_id=business.business_id,
                    objective=business.objective,
                    gateway=self.engine.llm,
                ),
                NegotiationAgent(
                    business_id=business.business_id,
                    objective=business.objective,
                    gateway=self.engine.llm,
                ),
                TreasuryAgent(business_id=business.business_id),
                RiskAgent(business_id=business.business_id),
                PaymentsAgent(business_id=business.business_id),
            ):
                if not business.agent_roles or agent.role in business.agent_roles:
                    self.registry.register(agent)
        elif business.role == "supplier":
            if not business.agent_roles or "supplier" in business.agent_roles:
                self.registry.register(
                    SupplierAgent(
                        business_id=business.business_id, objective=business.objective
                    )
                )
        for role in POLICIES:
            if role == "recovery" and business.role != "buyer":
                continue
            if business.agent_roles and role not in business.agent_roles:
                continue
            self.registry.register(
                OperationsAgent(business_id=business.business_id, role=role)
            )

    def _has_pending_need(self, business_id: str, item: str) -> bool:
        if any(
            session["item"] == item
            and session["status"] in {"negotiating", "agreement_proposed"}
            and self._session_pending(session)
            for session in self.store.negotiations(business_id)
        ):
            return True
        for contract in self.engine.contracts.values():
            if (
                contract.buyer_id == business_id
                and contract.item == item
                and contract.delivered_quantity < contract.quantity
                and getattr(contract, "fulfillment_state", "")
                in {"RESERVED", "SHIPPED", "PARTIALLY_RECEIVED"}
            ):
                return True
        return False

    def _session_pending(self, session: dict) -> bool:
        if session["status"] == "negotiating":
            return True
        task = next(
            (
                task
                for task in self.store.tasks()
                if task["task_id"] == session["task_id"]
            ),
            {},
        )
        return task.get("status") in {"queued", "waiting", "running"}

    def tick(self) -> list[dict[str, Any]]:
        if hasattr(self.engine, "advance_clock"):
            self.engine.advance_clock()
        else:
            self.engine.clock.advance(ticks=1)
        self._register_teams()
        actions: list[dict[str, Any]] = []
        context = AgentContext(self.engine, self.registry, actions)
        self.registry.drain(context)
        for event in self.engine.bus.replay():
            if event.type == "RecoveryRequested" and event.business_id:
                agent = self.registry.by_role(event.business_id, "recovery")
                if agent:
                    agent.recover(context, event)
        self.registry.drain(context)
        for contract in list(self.engine.contracts.values()):
            buyer = self.engine.businesses[contract.buyer_id]
            if not buyer.active:
                continue
            inventory = self.registry.by_role(contract.buyer_id, "inventory")
            if (
                inventory
                and contract.fulfillment_state
                in {"RESERVED", "SHIPPED", "PARTIALLY_RECEIVED"}
                and self.engine.clock.tick >= contract.due_tick
            ):
                try:
                    self.engine.deliver_contract(contract.contract_id)
                except ValueError as exc:
                    self.engine._emit(
                        "DeliveryException",
                        contract.buyer_id,
                        contract.contract_id,
                        payload={"reason": str(exc)},
                    )
            payments = self.registry.by_role(contract.buyer_id, "payments")
            if (
                payments
                and contract.fulfillment_state == "RECEIVED"
                and contract.payment_state in {"APPROVED", "FAILED"}
            ):
                try:
                    result = self.engine.pay_contract(contract.contract_id)
                    payments.decisions += 1

                except ValueError as exc:
                    self.engine._emit(
                        "PaymentException",
                        contract.buyer_id,
                        contract.contract_id,
                        payload={"reason": str(exc)},
                    )
            accounting = self.registry.by_role(contract.buyer_id, "accounting")
            if accounting and contract.payment_state == "CONFIRMED":
                try:
                    self.engine.reconcile_payment(contract.payment_id)
                    accounting.decisions += 1
                except ValueError as exc:
                    self.engine._emit(
                        "ReconciliationException",
                        contract.buyer_id,
                        contract.contract_id,
                        payload={"reason": str(exc)},
                    )
        for agent in self.registry.agents.values():
            if (
                isinstance(agent, OperationsAgent)
                and self.engine.businesses[agent.business_id].active
            ):
                agent.inspect(context)
        for session in self.store.negotiations():
            if (
                session["status"] == "negotiating"
                and session["deadline_tick"] < self.engine.clock.tick
            ):
                agent = self.registry.by_role(session["business_id"], "negotiation")
                if agent:
                    agent.expire(session, context)
        for business in self.engine.businesses.values():
            if business.role != "buyer" or not business.active:
                continue
            inventory = self.registry.by_role(business.business_id, "inventory")
            signal = (
                inventory.low_stock_signal(self.engine)
                if isinstance(inventory, InventoryAgent)
                else None
            )
            if signal is None or self._has_pending_need(
                business.business_id, signal["item"]
            ):
                continue
            correlation_id = f"need:{business.business_id}:{self.engine.clock.day}:{self.engine.clock.tick}"
            inventory.publish_need(context, signal, correlation_id=correlation_id)
        delivered = self.registry.drain(context)
        self.engine._emit(
            "SchedulerTick",
            payload={
                "clock": self.engine.clock.now(),
                "actions": len(actions),
                "delivered_messages": delivered,
                "agent_runtime": True,
            },
            idempotency_key=f"runtime-tick:{self.engine.clock.tick}",
        )
        for agent in self.registry.agents.values():
            self.store.save_agent(agent.status_snapshot())
        return actions

    def snapshot(self) -> dict[str, Any]:
        records = self.store.messages()
        snapshot = {
            "agents": self.registry.snapshot(),
            "tasks": self.store.tasks(),
            "messages": [
                {
                    **row["message"],
                    **{
                        key: row[key]
                        for key in (
                            "status",
                            "attempts",
                            "expires_tick",
                            "last_error",
                            "acknowledged_at",
                        )
                    },
                }
                for row in records
            ],
            "negotiations": self.store.negotiations(),
            "transport": {
                "mode": "durable_local_queue",
                "delivery_semantics": "at_least_once",
                "queued_messages": sum(
                    row["status"] in {"queued", "retry", "processing"}
                    for row in records
                ),
                "dead_letters": sum(row["status"] == "dead_letter" for row in records),
                "persistence": "sqlite" if self.store.path != ":memory:" else "memory",
                "network_verified": False,
            },
            "reasoning": self.engine.llm.usage_summary()
            if hasattr(self.engine.llm, "usage_summary")
            else {"configured_mode": self.engine.llm.mode, "local_policy": True},
        }

        def public(value):
            if isinstance(value, dict):
                return {
                    key: public(item)
                    for key, item in value.items()
                    if key != "private_rationale"
                }
            if isinstance(value, list):
                return [public(item) for item in value]
            return value

        return public(snapshot)
