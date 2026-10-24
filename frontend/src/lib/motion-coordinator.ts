/**
 * Agentropolis — Motion Event Coordinator
 *
 * Central presentation layer between backend economic events and visual
 * animations. Never authoritative over financial/economic state.
 *
 * Uses event IDs and sequence numbers to prevent duplicate visual events.
 * Supports animation interruption, event replay, and reconnection recovery.
 */

import type { EconomyEvent, EconomySummary } from '@/types/economy';
import { motionDuration, motionEase, motionSpring, motionLayers, type MotionTier, type MotionLayer } from './motion-design-system';

export type MotionEventHandler = (event: EconomyEvent, summary: EconomySummary | null) => void;

interface RegisteredAnimation {
  id: string;
  name: string;
  layer: MotionLayer;
  eventTypes: string[];
  handler: MotionEventHandler;
  cost: 'low' | 'medium' | 'high';
  duration: number;
}

interface MotionCoordinatorOptions {
  tier?: MotionTier;
  reducedMotion?: boolean;
}

export class MotionEventCoordinator {
  private handlers = new Map<string, RegisteredAnimation[]>();
  private processedSeqs = new Set<number>();
  private processedEventIds = new Set<string>();
  private summary: EconomySummary | null = null;
  private tier: MotionTier = 'high';
  private reducedMotion = false;
  private maxHistory = 2000;
  private seqCutoff = 0;

  constructor(options: MotionCoordinatorOptions = {}) {
    this.tier = options.tier ?? 'high';
    this.reducedMotion = options.reducedMotion ?? false;
  }

  /** Set the current authoritative summary (from backend). Never mutate state here. */
  setSummary(summary: EconomySummary | null) {
    this.summary = summary;
  }

  /** Set performance tier. High = full effects, balanced = reduced particles, minimal = transitions only. */
  setTier(tier: MotionTier) {
    this.tier = tier;
  }

  setReducedMotion(reduced: boolean) {
    this.reducedMotion = reduced;
  }

  /** Register an animation handler for specific event types. */
  register(animation: RegisteredAnimation) {
    for (const type of animation.eventTypes) {
      const entries = this.handlers.get(type) ?? [];
      this.handlers.set(type, [...entries.filter((entry) => entry.id !== animation.id), animation]);
    }
    return () => {
      for (const type of animation.eventTypes) {
        const remaining = (this.handlers.get(type) ?? []).filter((entry) => entry !== animation);
        if (remaining.length) this.handlers.set(type, remaining);
        else this.handlers.delete(type);
      }
    };
  }

  /**
   * Process a new backend event. Triggers matching animations.
   * Idempotent: same seq/eventId won't fire twice.
   */
  processEvent(event: EconomyEvent): void {
    // Deduplication by sequence number
    if (event.seq != null && event.seq <= this.seqCutoff) return;
    if (event.seq != null) this.seqCutoff = Math.max(this.seqCutoff, event.seq);

    // Deduplication by event ID
    const eventId = `${event.type}:${event.seq}:${event.business_id ?? 'global'}`;
    if (this.processedEventIds.has(eventId)) return;
    this.processedEventIds.add(eventId);

    // Keep history bounded
    if (this.processedEventIds.size > this.maxHistory) {
      const first = this.processedEventIds.values().next().value;
      if (first) this.processedEventIds.delete(first);
    }

    const handlers = this.handlers.get(event.type) ?? [];
    for (const handler of handlers) {
      // Skip expensive effects on minimal tier
      if (this.tier === 'minimal' && handler.cost === 'high') continue;
      // Reduce particle density on balanced tier
      if (this.tier === 'balanced' && handler.cost === 'high') continue;

      try {
        handler.handler(event, this.summary);
      } catch (err) {
        console.warn(`Motion handler ${handler.id} failed:`, err);
      }
    }
  }

  /** Replay a batch of events (e.g., after reconnection). Skips already-processed. */
  replayEvents(events: EconomyEvent[]): void {
    const sorted = [...events].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
    for (const event of sorted) {
      this.processEvent(event);
    }
  }

  /** Clear all processed event tracking (full reset). */
  reset() {
    this.processedSeqs.clear();
    this.processedEventIds.clear();
    this.seqCutoff = 0;
  }

  /** Get duration adjusted for tier and reduced motion. */
  getDuration(seconds: number): number {
    if (this.reducedMotion) return 0;
    if (this.tier === 'minimal') return Math.min(seconds, 0.1);
    if (this.tier === 'balanced') return Math.min(seconds, 0.4);
    return seconds;
  }

  /** Get ease curve. */
  getEase(key: keyof typeof motionEase) {
    return motionEase[key];
  }

  /** Get spring config. */
  getSpring(key: keyof typeof motionSpring) {
    return motionSpring[key];
  }

  /** Check if a layer is enabled given current tier. */
  isLayerEnabled(layer: MotionLayer): boolean {
    if (this.reducedMotion) return layer === motionLayers.interactive || layer === motionLayers.dataDriven;
    if (this.tier === 'minimal') return layer === motionLayers.interactive || layer === motionLayers.dataDriven;
    if (this.tier === 'balanced') return layer !== motionLayers.generative;
    return true;
  }
}

/** Singleton instance */
export const motionCoordinator = new MotionEventCoordinator();

/** Helper: create a standard registered animation */
export function registerAnimation({
  id,
  name,
  layer,
  eventTypes,
  handler,
  cost = 'low',
  duration = motionDuration.standard,
}: {
  id: string;
  name: string;
  layer: MotionLayer;
  eventTypes: string[];
  handler: MotionEventHandler;
  cost?: 'low' | 'medium' | 'high';
  duration?: number;
}) {
  motionCoordinator.register({ id, name, layer, eventTypes, handler, cost, duration });
}