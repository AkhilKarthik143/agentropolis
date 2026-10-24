/**
 * Agentropolis — Original Logo Mark
 *
 * "Neon cartography meets editorial science fiction."
 * A geometric constellation forming an abstract "A" with luminous pathways
 * connecting autonomous business nodes. Procedural pulse and slow rotation
 * keep it alive without demanding attention.
 */

import { motion, useReducedMotion, type TargetAndTransition } from 'motion/react';
import { useId, type CSSProperties } from 'react';

export function AgentropolisLogo({ size = 32, className = '', style }: { size?: number; className?: string; style?: CSSProperties }) {
  const reducedMotion = useReducedMotion();
  const id = useId();
  const gradientId = `${id}-gradient`;
  const glowId = `${id}-glow`;

  const rotate: TargetAndTransition = reducedMotion
    ? { rotate: 0 }
    : { rotate: [0, 360], transition: { duration: 20, repeat: Infinity, ease: 'linear' } };

  const pulse: TargetAndTransition = reducedMotion
    ? { opacity: 1 }
    : { opacity: [0.6, 1, 0.6], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' } };

  return (
    <motion.svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="Agentropolis"
      animate={rotate}
      style={style}
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ff6a00" />
          <stop offset="50%" stopColor="#8cf2c8" />
          <stop offset="100%" stopColor="#ff4757" />
        </linearGradient>
        <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Outer constellation ring — slowly rotating */}
      <motion.circle
        cx="32"
        cy="32"
        r="28"
        fill="none"
        stroke="rgba(140, 242, 200, 0.15)"
        strokeWidth="1"
        strokeDasharray="80 40"
        animate={pulse}
      />

      {/* Connecting pathways — the "A" crossbar and legs */}
      <g filter={`url(#${glowId})`}>
        <path
          d="M 16 52 L 32 12 L 48 52"
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 22 32 L 42 32"
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </g>

      {/* Nodes — autonomous business points at pathway intersections */}
      <g>
        <motion.circle cx="32" cy="12" r="3" fill="#fff" animate={pulse} />
        <motion.circle cx="16" cy="52" r="3" fill="#fff" animate={{ ...pulse, transition: { ...pulse.transition, delay: reducedMotion ? 0 : 0.6 } }} />
        <motion.circle cx="48" cy="52" r="3" fill="#fff" animate={{ ...pulse, transition: { ...pulse.transition, delay: reducedMotion ? 0 : 1.2 } }} />
        <motion.circle cx="22" cy="32" r="2.5" fill="#ff6a00" animate={{ ...pulse, transition: { ...pulse.transition, delay: reducedMotion ? 0 : 0.3 } }} />
        <motion.circle cx="42" cy="32" r="2.5" fill="#8cf2c8" animate={{ ...pulse, transition: { ...pulse.transition, delay: reducedMotion ? 0 : 0.9 } }} />
      </g>

      {/* Tiny orbiting indicators — AI employees */}
      <motion.circle cx="32" cy="12" r="7" fill="none" stroke="#ff6a00" strokeWidth="1" strokeDasharray="4 4" animate={pulse} />
    </motion.svg>
  );
}

/**
 * Compact wordmark used in the shell and headers.
 */
export function AgentropolisWordmark({ className = '' }: { className?: string }) {
  return (
    <span className={className} style={{ letterSpacing: '-0.05em' }}>
      <span style={{ color: '#ededed', fontWeight: 600 }}>Agentro</span>
      <span style={{ color: '#ff6a00', fontWeight: 600 }}>polis</span>
    </span>
  );
}