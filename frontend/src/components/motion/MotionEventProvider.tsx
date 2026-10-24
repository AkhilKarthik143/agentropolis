/**
 * Agentropolis — Motion Event Provider
 *
 * React context provider that bridges backend economy events to the MotionEventCoordinator.
 * Wraps useEconomyEvents and feeds each new event to the animation coordinator.
 *
 * Individual animation effects subscribe to the coordinator via registerAnimation().
 */

import React, { useEffect, useState, createContext, useContext } from 'react';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import { MotionEventCoordinator, type MotionEventHandler } from '@/lib/motion-coordinator';
import type { EconomySummary } from '@/types/economy';

interface MotionEventProviderProps {
  children: React.ReactNode;
  tier?: 'high' | 'balanced' | 'minimal';
}

interface MotionContextType {
  coordinator: MotionEventCoordinator;
  summary: EconomySummary | null;
  loading: boolean;
  connected: boolean;
  error: string | null;
  refresh: () => void;
}

const MotionContext = createContext<MotionContextType | null>(null);

export function MotionEventProvider({ children, tier = 'high' }: MotionEventProviderProps) {
  const { summary, events, loading, connected, error, refresh } = useEconomyEvents();
  const [coordinator] = useState(() => new MotionEventCoordinator({ tier }));

  useEffect(() => {
    coordinator.setTier(tier);
  }, [tier, coordinator]);

  useEffect(() => {
    coordinator.setSummary(summary ?? null);
  }, [summary, coordinator]);

  useEffect(() => {
    if (!events || events.length === 0) return;
    for (const event of events) {
      coordinator.processEvent(event);
    }
  }, [events, coordinator]);

  return (
    <MotionContext.Provider value={{ coordinator, summary, loading, connected, error, refresh }}>
      {children}
    </MotionContext.Provider>
  );
}

export function useMotionCoordinator(): MotionContextType {
  const ctx = useContext(MotionContext);
  if (!ctx) throw new Error('useMotionCoordinator must be used within MotionEventProvider');
  return ctx;
}

/**
 * Convenience hook: register an animation effect that responds to backend events.
 * Automatically cleans up on unmount.
 */
export function useMotionEffect({
  id,
  name,
  layer,
  eventTypes,
  handler,
  cost = 'low',
  duration = 0.24,
}: {
  id: string;
  name: string;
  layer: 'ambient' | 'interactive' | 'data-driven' | 'cinematic' | 'generative';
  eventTypes: string[];
  handler: MotionEventHandler;
  cost?: 'low' | 'medium' | 'high';
  duration?: number;
}) {
  const { coordinator } = useMotionCoordinator();

  React.useEffect(() => {
    const reg = { id, name, layer, eventTypes, handler, cost, duration };
    return coordinator.register(reg);
  }, [coordinator, id, name, layer, eventTypes, handler, cost, duration]);
}