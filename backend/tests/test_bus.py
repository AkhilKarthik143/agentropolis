import asyncio

from app.events.bus import EventBus
from app.events.schemas import EventEnvelope
from app.events.store import MemoryStore


def test_event_bus_orders_and_deduplicates():
    bus = EventBus(MemoryStore())
    first = bus.append(EventEnvelope(type="NeedDetected", idempotency_key="need:1"))
    duplicate = bus.append(EventEnvelope(type="NeedDetected", idempotency_key="need:1"))
    second = bus.append(EventEnvelope(type="OfferCreated"))
    assert duplicate.seq == first.seq
    assert [event.seq for event in bus.replay()] == [1, 2]
    assert bus.replay(1)[0].type == second.type


def test_event_bus_backfills_subscriber():
    async def scenario():
        bus = EventBus(MemoryStore())
        bus.append(EventEnvelope(type="NeedDetected"))
        stream = bus.subscribe(0)
        first = await stream.__anext__()
        bus.append(EventEnvelope(type="OfferCreated"))
        second = await stream.__anext__()
        await stream.aclose()
        return first, second

    first, second = asyncio.run(scenario())
    assert (first.seq, second.seq) == (1, 2)

