/**
 * Agentropolis — Business Node
 *
 * Industry-specific animated business entities. Each industry has a unique
 * procedural motif:
 * 
 * - Bank: geometric vault pattern
 * - Logistics: moving directional pathways
 * - Retailer: animated storefront motif
 * - Research: rotating abstract data structure
 * - Supplier: moving inventory/production indicators
 * - Default: constellation node
 *
 * Nodes respond to business state: active, disrupted, negotiating, recovering.
 */

import { motion, useReducedMotion, type TargetAndTransition } from 'motion/react';
import type { Ref, MouseEventHandler } from 'react';
import type { EconomyBusiness } from '@/types/economy';

type Industry = 'bank' | 'logistics' | 'retail' | 'research' | 'supplier' | 'default';

interface BusinessNodeProps {
  business: EconomyBusiness;
  ref?: Ref<HTMLDivElement>;
  className?: string;
  onMouseEnter?: MouseEventHandler<HTMLDivElement>;
  onMouseLeave?: MouseEventHandler<HTMLDivElement>;
  x: number;
  y: number;
  state?: 'active' | 'disrupted' | 'negotiating' | 'recovering' | 'offline';
  selected?: boolean;
  onClick?: () => void;
  size?: number;
}

function getIndustry(business: EconomyBusiness): Industry {
  const kind = (business.kind ?? '').toLowerCase();
  const categories = (business.categories ?? []).map((c) => c.toLowerCase());
  const all = `${kind} ${categories.join(' ')}`;

  if (all.includes('bank') || all.includes('finance') || all.includes('treasury')) return 'bank';
  if (all.includes('logistics') || all.includes('shipping') || all.includes('transport') || all.includes('freight')) return 'logistics';
  if (all.includes('retail') || all.includes('shop') || all.includes('store') || all.includes('cafe') || all.includes('market')) return 'retail';
  if (all.includes('research') || all.includes('lab') || all.includes('data') || all.includes('analytics')) return 'research';
  if (all.includes('supplier') || all.includes('supply') || all.includes('vendor') || all.includes('wholesale')) return 'supplier';
  return 'default';
}

const industryColors: Record<Industry, string> = {
  bank: '#f59e0b',
  logistics: '#ffbe76',
  retail: '#8cf2c8',
  research: '#c49bea',
  supplier: '#ff6348',
  default: '#ff6a00',
};

const industryGlow: Record<Industry, string> = {
  bank: 'rgba(245, 158, 11, 0.4)',
  logistics: 'rgba(255, 190, 118, 0.4)',
  retail: 'rgba(140, 242, 200, 0.4)',
  research: 'rgba(196, 155, 234, 0.4)',
  supplier: 'rgba(255, 99, 72, 0.4)',
  default: 'rgba(255, 106, 0, 0.4)',
};

export function BusinessNode({ business, x, y, state = 'active', selected = false, onClick, size = 44, ref, className = '', onMouseEnter, onMouseLeave }: BusinessNodeProps) {
  const reducedMotion = useReducedMotion() ?? false;
  const industry = getIndustry(business);
  const color = industryColors[industry];
  const glow = industryGlow[industry];

  const pulseVariants: { hidden: TargetAndTransition; visible: TargetAndTransition } = reducedMotion
    ? { hidden: {}, visible: {} }
    : {
        hidden: { scale: 0.8, opacity: 0 },
        visible: {
          scale: 1,
          opacity: 1,
          transition: { duration: 0.3, ease: 'backOut' },
          ...animateState(state),
        },
      };

  const isDisrupted = state === 'disrupted';
  const isNegotiating = state === 'negotiating';
  const isRecovering = state === 'recovering';
  const isOffline = state === 'offline';

  return (
    <motion.div
      ref={ref}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onClick?.(); } }}
      className={`business-node business-node-${industry} business-node-${state} ${selected ? 'selected' : ''} ${className ?? ''}`}
      style={{
        left: `${x - size / 2}px`,
        top: `${y - size / 2}px`,
        width: `${size}px`,
        height: `${size}px`,
        boxShadow: selected || isNegotiating || isRecovering ? `0 0 20px ${glow}` : `0 0 12px ${glow}`,
        filter: isOffline ? 'grayscale(0.8) opacity(0.6)' : isDisrupted ? 'hue-rotate(40deg)' : 'none',
      }}
      animate={pulseVariants.visible}
      initial={pulseVariants.hidden}
      exit={{ opacity: 0, scale: 0.8, transition: { duration: reducedMotion ? 0 : 0.2 } }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`${business.name} — ${business.kind} — ${state}`}
    >
      <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
        <defs>
          <linearGradient id={`node-grad-${business.business_id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor={adjustColor(color, -30)} />
          </linearGradient>
        </defs>

        {/* Outer ring — activity indicator */}
        <motion.circle
          cx="32"
          cy="32"
          r="26"
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeOpacity={selected ? 0.8 : 0.3}
          strokeDasharray={isNegotiating || isRecovering ? '8 6' : '0 0'}
          animate={{
            strokeDashoffset: !reducedMotion && (isNegotiating || isRecovering) ? [0, 14] : 0,
            transition: { duration: 2, repeat: Infinity, ease: 'linear' },
          }}
        />

        {/* Industry motif */}
        {renderIndustryMotif(industry, color, reducedMotion)}

        {/* Inner core — business health */}
        <motion.circle
          cx="32"
          cy="32"
          r={selected ? 10 : 7}
          fill="#000"
          stroke="#fff"
          strokeWidth="1.5"
          animate={{
            scale: isDisrupted && !reducedMotion ? [1, 0.7, 1] : 1,
            fill: isDisrupted ? '#ff4757' : selected ? '#fff' : color,
            transition: { duration: reducedMotion ? 0 : 2, repeat: isDisrupted ? Infinity : 0, ease: 'easeInOut' },
          }}
        />

        {/* Tiny orbiting indicators — AI employees */}
        <motion.circle
          cx="32"
          cy="12"
          r="2.5"
          fill={color}
          animate={{
            rotate: reducedMotion ? 0 : [0, 360],
            transition: { duration: 4, repeat: Infinity, ease: 'linear' },
          }}
        />
        <motion.circle
          cx="44"
          cy="32"
          r="2"
          fill={color}
          animate={{
            rotate: reducedMotion ? 0 : [0, 360],
            transition: { duration: 5, repeat: Infinity, ease: 'linear', delay: 1 },
          }}
        />
      </svg>

      {/* Business label */}
      <motion.div
        className="business-node-label"
        animate={{
          opacity: selected ? 1 : 0,
          y: selected ? -8 : -4,
          transition: { duration: reducedMotion ? 0 : 0.2 },
        }}
        style={{
          position: 'absolute',
          bottom: `-24px`,
          left: '50%',
          transform: 'translateX(-50%)',
          whiteSpace: 'nowrap',
          fontSize: 11,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          color: isOffline ? '#666' : '#ededed',
          pointerEvents: 'none',
          textShadow: '0 0 8px rgba(0,0,0,0.8)',
        }}
      >
        {business.name.length > 14 ? `${business.name.slice(0, 14)}…` : business.name}
      </motion.div>
    </motion.div>
  );
}

function animateState(state: string): TargetAndTransition {
  switch (state) {
    case 'disrupted':
      return {
        scale: [1, 0.85, 1],
        transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
      };
    case 'negotiating':
      return {
        scale: [1, 1.1, 1],
        transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
      };
    case 'recovering':
      return {
        scale: [1, 1.15, 1],
        transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' },
      };
    default:
      return {};
  }
}

function adjustColor(hex: string, amount: number): string {
  return hex.replace(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i, (_, r, g, b) => {
    const clamp = (v: number) => Math.max(0, Math.min(255, v));
    const rr = clamp(parseInt(r, 16) + amount);
    const gg = clamp(parseInt(g, 16) + amount);
    const bb = clamp(parseInt(b, 16) + amount);
    return `#${rr.toString(16).padStart(2, '0')}${gg.toString(16).padStart(2, '0')}${bb.toString(16).padStart(2, '0')}`;
  });
}

function renderIndustryMotif(industry: Industry, color: string, reducedMotion: boolean) {
  const baseStyle = { fill: 'none', stroke: color, strokeWidth: '2', strokeLinecap: 'round', strokeLinejoin: 'round' } as const;

  switch (industry) {
    case 'bank': {
      return (
        <g>
          <motion.rect
            x="18"
            y="18"
            width="28"
            height="28"
            rx="3"
            {...baseStyle}
            strokeOpacity={0.6}
            animate={{
              scale: reducedMotion ? 1 : [1, 1.03, 1],
              transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
            }}
          />
          <motion.line x1="26" y1="26" x2="38" y2="26" {...baseStyle} strokeWidth="3" />
          <motion.line x1="32" y1="20" x2="32" y2="44" {...baseStyle} strokeWidth="3" />
        </g>
      );
    }
    case 'logistics': {
      return (
        <g>
          <motion.path
            d="M 16 32 L 32 16 L 48 32"
            {...baseStyle}
            strokeDasharray="12"
            animate={{
              strokeDashoffset: reducedMotion ? 0 : [0, -24],
              transition: { duration: 2, repeat: Infinity, ease: 'linear' },
            }}
          />
          <motion.circle cx="32" cy="16" r="3" fill="#fff" animate={{ opacity: reducedMotion ? 1 : [0, 1, 0], transition: { duration: 1, repeat: Infinity } } } />
        </g>
      );
    }
    case 'retail': {
      return (
        <g>
          <motion.rect x="20" y="24" width="24" height="20" rx="2" {...baseStyle} strokeOpacity="0.5" />
          <motion.rect x="26" y="16" width="12" height="8" fill={color} />
          <motion.rect x="28" y="28" width="4" height="6" fill={color} opacity="0.7" />
          <motion.rect x="32" y="28" width="4" height="6" fill={color} opacity="0.7" />
        </g>
      );
    }
    case 'research': {
      return (
        <motion.g
          animate={{
            rotate: reducedMotion ? 0 : [0, 360],
            transition: { duration: 5, repeat: Infinity, ease: 'linear' },
          }}
        >
          <motion.circle cx="32" cy="32" r="12" {...baseStyle} strokeOpacity="0.4" />
          <motion.circle cx="32" cy="20" r="4" fill={color} />
          <motion.circle cx="42" cy="32" r="4" fill={color} opacity="0.6" />
          <motion.circle cx="32" cy="44" r="4" fill={color} opacity="0.6" />
          <motion.circle cx="22" cy="32" r="4" fill={color} opacity="0.6" />
        </motion.g>
      );
    }
    case 'supplier': {
      return (
        <g>
          <motion.rect x="24" y="20" width="16" height="24" rx="2" {...baseStyle} strokeOpacity="0.5" />
          <motion.rect x="26" y="22" width="12" height="6" fill={color} />
          <motion.rect x="26" y="30" width="12" height="6" fill={color} opacity="0.7" />
          <motion.rect x="26" y="38" width="12" height="6" fill={color} opacity="0.5" />
        </g>
      );
    }
    default: {
      return (
        <g>
          <motion.circle cx="32" cy="32" r="14" fill="none" stroke={color} strokeWidth="2" strokeOpacity="0.4" />
          <motion.circle cx="32" cy="32" r="6" fill={color} opacity="0.8" />
        </g>
      );
    }
  }
}