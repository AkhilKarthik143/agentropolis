"""Explicit negotiation/session transitions for the Agentropolis demo.

Agents can recommend a next action, but only the engine may call ``transition``.
Keeping the transition table separate makes illegal recovery shortcuts visible in
tests and in the audit trail.
"""

from __future__ import annotations

from enum import StrEnum


class EconomyState(StrEnum):
    INVENTORY_LOW = "INVENTORY_LOW"
    OFFERS_REQUESTED = "OFFERS_REQUESTED"
    NEGOTIATING = "NEGOTIATING"
    PROPOSED = "PROPOSED"
    TREASURY_CHECK = "TREASURY_CHECK"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONTRACTED = "CONTRACTED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    AWAITING_DELIVERY = "AWAITING_DELIVERY"
    DELIVERED = "DELIVERED"
    SUPPLIER_BANKRUPT = "SUPPLIER_BANKRUPT"
    RECOVERY_NEGOTIATION = "RECOVERY_NEGOTIATION"
    REPLACEMENT_CONTRACT = "REPLACEMENT_CONTRACT"
    RECOVERED = "RECOVERED"


LEGAL_TRANSITIONS: dict[EconomyState, frozenset[EconomyState]] = {
    EconomyState.INVENTORY_LOW: frozenset({EconomyState.OFFERS_REQUESTED}),
    EconomyState.OFFERS_REQUESTED: frozenset({EconomyState.NEGOTIATING}),
    EconomyState.NEGOTIATING: frozenset({EconomyState.PROPOSED, EconomyState.TREASURY_CHECK}),
    EconomyState.PROPOSED: frozenset({EconomyState.TREASURY_CHECK, EconomyState.NEGOTIATING}),
    # CONTRACTED remains as a compatibility edge for previously recorded deals.
    # callers; new Agentropolis paths emit APPROVED/REJECTED explicitly first.
    EconomyState.TREASURY_CHECK: frozenset({EconomyState.APPROVED, EconomyState.REJECTED, EconomyState.CONTRACTED}),
    EconomyState.APPROVED: frozenset({EconomyState.CONTRACTED}),
    EconomyState.REJECTED: frozenset({EconomyState.NEGOTIATING}),
    EconomyState.CONTRACTED: frozenset({EconomyState.PAYMENT_RECORDED}),
    EconomyState.PAYMENT_RECORDED: frozenset({EconomyState.AWAITING_DELIVERY, EconomyState.DELIVERED}),
    EconomyState.AWAITING_DELIVERY: frozenset({EconomyState.DELIVERED, EconomyState.SUPPLIER_BANKRUPT, EconomyState.RECOVERED}),
    EconomyState.DELIVERED: frozenset(),
    EconomyState.SUPPLIER_BANKRUPT: frozenset({EconomyState.RECOVERY_NEGOTIATION}),
    EconomyState.RECOVERY_NEGOTIATION: frozenset({EconomyState.REPLACEMENT_CONTRACT}),
    EconomyState.REPLACEMENT_CONTRACT: frozenset({EconomyState.PAYMENT_RECORDED, EconomyState.RECOVERED}),
    EconomyState.RECOVERED: frozenset(),
}


class IllegalTransition(ValueError):
    pass


def transition(current: EconomyState | str, target: EconomyState | str) -> EconomyState:
    """Validate and return ``target``; no state is mutated here."""

    current_state = EconomyState(current)
    target_state = EconomyState(target)
    if target_state not in LEGAL_TRANSITIONS[current_state]:
        raise IllegalTransition(f"illegal economy transition {current_state} -> {target_state}")
    return target_state


def can_transition(current: EconomyState | str, target: EconomyState | str) -> bool:
    try:
        transition(current, target)
    except (ValueError, IllegalTransition):
        return False
    return True
