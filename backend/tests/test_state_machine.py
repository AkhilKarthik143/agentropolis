import pytest

from app.economy.state_machine import EconomyState, IllegalTransition, can_transition, transition


def test_recovery_path_is_explicit_and_legal():
    path = [
        (EconomyState.INVENTORY_LOW, EconomyState.OFFERS_REQUESTED),
        (EconomyState.OFFERS_REQUESTED, EconomyState.NEGOTIATING),
        (EconomyState.NEGOTIATING, EconomyState.PROPOSED),
        (EconomyState.PROPOSED, EconomyState.TREASURY_CHECK),
        (EconomyState.TREASURY_CHECK, EconomyState.CONTRACTED),
        (EconomyState.CONTRACTED, EconomyState.PAYMENT_RECORDED),
        (EconomyState.PAYMENT_RECORDED, EconomyState.AWAITING_DELIVERY),
        (EconomyState.AWAITING_DELIVERY, EconomyState.SUPPLIER_BANKRUPT),
        (EconomyState.SUPPLIER_BANKRUPT, EconomyState.RECOVERY_NEGOTIATION),
        (EconomyState.RECOVERY_NEGOTIATION, EconomyState.REPLACEMENT_CONTRACT),
        (EconomyState.REPLACEMENT_CONTRACT, EconomyState.PAYMENT_RECORDED),
    ]
    assert all(can_transition(current, target) for current, target in path)
    assert transition(EconomyState.RECOVERY_NEGOTIATION, EconomyState.REPLACEMENT_CONTRACT) is EconomyState.REPLACEMENT_CONTRACT


def test_illegal_transition_is_rejected():
    with pytest.raises(IllegalTransition):
        transition(EconomyState.DELIVERED, EconomyState.TREASURY_CHECK)
