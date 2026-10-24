from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from app.agents.base import AgentContext
from app.agents.supplier import SupplierAgent
from app.api.economy import EconomyRuntime
from app.events.schemas import AgentMessage, AgentMessageType, AgentTask
from app.orchestration.store import RuntimeStore


def message(simulation='one', key='once'):
    return AgentMessage(message_id=f'msg:{key}', message_type=AgentMessageType.INVENTORY_LOW, sender_id='inventory_agent:cafe_lumen', recipient_id='manager_agent:cafe_lumen', business_id='cafe_lumen', simulation_id=simulation, idempotency_key=key, payload={'item': 'coffee_beans', 'required_quantity': 12})


def test_queue_survives_restart_and_idempotency_is_scoped_to_simulation(tmp_path):
    path = tmp_path / 'runtime.db'
    first = RuntimeStore('one', path)
    assert first.enqueue(message(), tick=1)
    assert not first.enqueue(message(), tick=1)
    first.close()
    recovered = RuntimeStore('one', path)
    claimed = recovered.claim(1)
    assert claimed['message']['message_id'] == 'msg:once'
    recovered.acknowledge('msg:once')
    assert recovered.claim(2) is None
    other = RuntimeStore('two', path)
    assert other.enqueue(message('two'), tick=1)
    assert other.claim(1)['message']['simulation_id'] == 'two'
    assert recovered.messages()[0]['status'] == 'acknowledged'


def test_expired_worker_lease_is_recovered_and_old_owner_cannot_ack(tmp_path):
    first = RuntimeStore('one', tmp_path / 'runtime.db')
    first.enqueue(message(), tick=0)
    first.claim(0, now=100, lease_seconds=5)
    second = RuntimeStore('one', tmp_path / 'runtime.db')
    assert second.claim(0, now=104) is None
    recovered = second.claim(0, now=106)
    assert recovered['attempts'] == 2
    with pytest.raises(RuntimeError, match='lease was lost'):
        first.acknowledge('msg:once')
    second.acknowledge('msg:once')


def test_claim_is_atomic_between_workers(tmp_path):
    path = tmp_path / 'queue.db'
    first, second = RuntimeStore('one', path), RuntimeStore('one', path)
    first.enqueue(message(), tick=0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda store: store.claim(0), [first, second]))
    assert sum(result is not None for result in results) == 1


def test_retry_backoff_dead_letter_and_expiration():
    store = RuntimeStore('one')
    store.enqueue(message(), tick=0)
    for tick in (0, 1, 3):
        assert store.claim(tick)
        status = store.fail('msg:once', tick=tick, error='temporary unavailable')
        assert store.claim(tick) is None
    assert status == 'dead_letter'
    store.enqueue(message(key='late'), tick=0, ttl=2)
    assert store.expire(3)[0]['message']['message_id'] == 'msg:late'
    assert store.claim(3) is None


def test_durable_tasks_negotiation_and_private_memory_survive_restart(tmp_path):
    path = tmp_path / 'runtime.db'
    store = RuntimeStore('one', path)
    task = AgentTask(task_type='source', business_id='buyer', assigned_agent_id='procurement:buyer')
    store.save_task(task)
    store.update_task(task.task_id, 'waiting', {'pending': 'quotes'})
    store.save_negotiation({'negotiation_id': 'n1', 'business_id': 'buyer', 'status': 'negotiating', 'rounds': {'supplier': 2}})
    store.remember('supplier', 'floor', 3000)
    store.close()
    recovered = RuntimeStore('one', path)
    assert recovered.tasks()[0]['status'] == 'waiting'
    assert recovered.negotiation('n1')['rounds']['supplier'] == 2
    assert recovered.recall('supplier', 'floor') == 3000
    assert RuntimeStore('two', path).tasks() == []


def test_roles_cannot_self_grant_permissions_or_impersonate_another_business():
    runtime = EconomyRuntime(store_mode='memory')
    registry = runtime.agent_runtime.registry
    procurement = registry.by_role('cafe_lumen', 'procurement')
    procurement.permissions += ('submit_approved_payment',)
    with pytest.raises(PermissionError):
        registry.require(procurement.agent_id, 'submit_approved_payment', 'cafe_lumen')
    context = AgentContext(runtime.engine, registry)
    registry.active_agent_id = procurement.agent_id
    with pytest.raises(PermissionError, match='impersonate'):
        context.send(message_type=AgentMessageType.INVENTORY_LOW, sender_id='inventory_agent:cafe_lumen', recipient_id='manager_agent:cafe_lumen', business_id='cafe_lumen', payload={})
    registry.active_agent_id = None
    with pytest.raises(PermissionError, match='another simulation'):
        registry.store.enqueue(message('wrong'), tick=0)


def test_independent_suppliers_exchange_actual_counteroffers_and_acknowledge():
    runtime = EconomyRuntime(store_mode='memory')
    actions = runtime.engine.tick()
    assert actions[0]['status'] == 'executed'
    snapshot = runtime.agent_runtime.snapshot()
    negotiation = snapshot['negotiations'][0]
    assert len(negotiation['expected_suppliers']) >= 2
    assert all(round_number >= 2 for round_number in negotiation['rounds'].values())
    assert snapshot['tasks'][0]['assigned_agent_id'] == 'procurement_agent:harbor_foods'
    assert snapshot['tasks'][0]['status'] == 'completed'
    assert all(value['status'] == 'acknowledged' for value in snapshot['messages'])
    supplier_quotes = [value for value in snapshot['messages'] if value['message_type'] == 'QUOTE']
    assert len({value['sender_id'] for value in supplier_quotes}) >= 2
    assert any(value['message_type'] == 'COUNTER_OFFER' for value in snapshot['messages'])


def test_supplier_quote_changes_with_current_capacity_and_cost():
    runtime = EconomyRuntime(store_mode='memory')
    business = runtime.engine.businesses['northstar_roasters']
    agent = SupplierAgent(business_id=business.business_id)
    initial = agent.quote(business, item='coffee_beans', quantity=12)
    business.capacity['coffee_beans'] = 12
    if 'coffee_beans' in business.inventory.quantities:
        business.inventory.quantities['coffee_beans'] = 36
    scarce = agent.quote(business, item='coffee_beans', quantity=12)
    assert scarce.unit_price_cents > initial.unit_price_cents
    assert scarce.delivery_days > initial.delivery_days
    business.active = False
    assert agent.quote(business, item='coffee_beans', quantity=12) is None


def test_buyer_can_reject_all_supplier_offers_without_a_purchase():
    runtime = EconomyRuntime(store_mode='memory')
    buyer = runtime.engine.businesses['cafe_lumen']
    buyer.spend_limit_cents = 10
    runtime.engine.businesses['harbor_foods'].spend_limit_cents = 10
    runtime.engine.shock('supplier_bankruptcy','northstar_roasters')
    before = len(runtime.engine.contracts)
    assert runtime.engine.tick() == []
    assert len(runtime.engine.contracts) == before
    assert runtime.agent_runtime.snapshot()['negotiations'][0]['status'] == 'rejected'
    assert runtime.agent_runtime.snapshot()['tasks'][0]['status'] == 'failed'


def test_negotiation_deadline_expires_when_supplier_never_responds():
    runtime = EconomyRuntime(store_mode='memory')
    store = runtime.agent_runtime.store
    task = AgentTask(task_type='source', business_id='cafe_lumen', assigned_agent_id='procurement_agent:cafe_lumen')
    store.save_task(task)
    store.save_negotiation({'negotiation_id': 'silent', 'business_id': 'cafe_lumen', 'item': 'coffee_beans', 'task_id': task.task_id, 'status': 'negotiating', 'deadline_tick': 0, 'offers': {}})
    runtime.engine.tick()
    assert store.negotiation('silent')['status'] == 'expired'
    assert next(value for value in store.tasks() if value['task_id'] == task.task_id)['status'] == 'failed'


def test_handler_failure_retries_without_false_acknowledgement(monkeypatch):
    runtime = EconomyRuntime(store_mode='memory')
    registry = runtime.agent_runtime.registry
    context = AgentContext(runtime.engine, registry)
    manager = registry.by_role('cafe_lumen', 'manager')
    original = manager.handle_message
    def unavailable(*_):
        raise TimeoutError('worker unavailable')
    monkeypatch.setattr(manager, 'handle_message', unavailable)
    registry.send(message(runtime.engine.session_id), context)
    assert registry.drain(context) == 0
    assert registry.store.messages()[0]['status'] == 'retry'
    monkeypatch.setattr(manager, 'handle_message', original)
    runtime.engine.clock.advance(ticks=1)
    assert registry.drain(context) > 0
    assert registry.store.messages()[0]['status'] == 'acknowledged'
    assert registry.store.messages()[0]['attempts'] == 2
