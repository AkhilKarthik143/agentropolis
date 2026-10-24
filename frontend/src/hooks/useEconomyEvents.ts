import { useCallback, useEffect, useRef, useState } from 'react';
import { getEconomyEvents, getEconomySummary } from '@/lib/economy-api';
import type { EconomyEvent, EconomySummary } from '@/types/economy';

function mergeEvents(current: EconomyEvent[], incoming: EconomyEvent[]) {
  const bySeq = new Map(current.map((event) => [event.seq, event]));
  incoming.filter((event) => event.type !== 'heartbeat').forEach((event) => bySeq.set(event.seq, event));
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq).slice(-600);
}

export function useEconomyEvents() {
  const [summary, setSummary] = useState<EconomySummary | null>(null);
  const [events, setEvents] = useState<EconomyEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastSeq = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const [nextSummary, nextEvents] = await Promise.all([getEconomySummary(), getEconomyEvents(0)]);
      setSummary(nextSummary);
      setEvents(nextEvents.slice(-600));
      lastSeq.current = nextEvents.at(-1)?.seq ?? 0;
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not connect to Agentropolis');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;
    let summaryTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (cancelled) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/simulations/demo_001?since=${lastSeq.current}`);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as EconomyEvent;
        if (event.type === 'heartbeat') return;
        if (event.type === 'resync') {
          void refresh();
          return;
        }
        lastSeq.current = Math.max(lastSeq.current, event.seq ?? 0);
        setEvents((current) => mergeEvents(current, [event]));
        if (!summaryTimer) summaryTimer = setTimeout(() => {
          summaryTimer = undefined;
          void getEconomySummary().then(setSummary).catch(() => undefined);
        }, 180);
      };
      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) reconnectTimer = setTimeout(connect, 1500);
      };
      socket.onerror = () => setConnected(false);
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (summaryTimer) clearTimeout(summaryTimer);
      socket?.close();
    };
  }, [refresh]);

  return { summary, events, loading, connected, error, refresh };
}

