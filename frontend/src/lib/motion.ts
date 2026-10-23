export const motionTokens = {
  duration: {
    instant: 0.14,
    fast: 0.18,
    standard: 0.22,
    panel: 0.28,
    expressive: 0.62,
  },
  ease: {
    out: [0.33, 1, 0.68, 1] as const,
    softOut: [0.16, 1, 0.3, 1] as const,
    inOut: 'easeInOut' as const,
  },
} as const;

export function motionDuration(reducedMotion: boolean | null, duration: number) {
  return reducedMotion ? 0 : duration;
}
