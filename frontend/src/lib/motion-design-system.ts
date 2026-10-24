/**
 * Agentropolis — Central Motion Design System
 *
 * Single source of truth for timing, easing, springs, and performance tiers.
 * All animation layers reference these tokens so the experience stays coherent.
 */

export type MotionTier = 'high' | 'balanced' | 'minimal';

/** ── Timing (seconds) ── */
export const motionDuration = {
  instant: 0.08,
  micro: 0.12,
  fast: 0.16,
  standard: 0.24,
  panel: 0.32,
  expressive: 0.5,
  cinematic: 0.8,
  slow: 1.2,
} as const;

/** ── Easing curves ── */
export const motionEase = {
  out: [0.33, 1, 0.68, 1] as const,
  softOut: [0.16, 1, 0.3, 1] as const,
  inOut: [0.43, 0.16, 0.58, 1] as const,
  backOut: [0.34, 1.56, 0.64, 1] as const,
  bounce: [0.68, -0.55, 0.27, 1.55] as const,
  circOut: [0.08, 0.82, 0.17, 1] as const,
} as const;

/** ── Spring presets ── */
export const motionSpring = {
  gentle: { stiffness: 120, damping: 18, mass: 0.8 },
  crisp: { stiffness: 300, damping: 26, mass: 0.5 },
  bouncy: { stiffness: 260, damping: 20, mass: 0.9 },
  fluid: { stiffness: 180, damping: 22, mass: 1.0 },
  slow: { stiffness: 80, damping: 20, mass: 1.2 },
} as const;

/** ── Performance tier overrides ── */
export function motionForTier(tier: MotionTier | null) {
  const base = {
    duration: motionDuration,
    ease: motionEase,
    spring: motionSpring,
  };
  if (tier === 'minimal') {
    return {
      ...base,
      duration: { ...motionDuration, panel: 0, expressive: 0, cinematic: 0, slow: 0 },
    };
  }
  if (tier === 'balanced') {
    return {
      ...base,
      duration: { ...motionDuration, cinematic: 0.4, slow: 0.6 },
    };
  }
  return base;
}

/** ── Reduced motion helper ── */
export function motionDurationFor(reducedMotion: boolean | null, seconds: number) {
  return reducedMotion ? 0 : seconds;
}

/** ── Layer definitions ── */
export const motionLayers = {
  ambient: 'ambient',
  interactive: 'interactive',
  dataDriven: 'data-driven',
  cinematic: 'cinematic',
  generative: 'generative',
} as const;

export type MotionLayer = (typeof motionLayers)[keyof typeof motionLayers];

/** ── Animation registry entry ── */
export interface AnimationRegistryEntry {
  id: string;
  name: string;
  screen: string;
  trigger: string;
  component: string;
  technology: 'framer-motion' | 'svg' | 'canvas' | 'css';
  layer: MotionLayer;
  eventSource?: string;
  duration: number;
  reducedMotion: string;
  performanceCost: 'low' | 'medium' | 'high';
  implemented: boolean;
  notes?: string;
}