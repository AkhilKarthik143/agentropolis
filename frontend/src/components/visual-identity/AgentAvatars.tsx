/**
 * Agentropolis — Original AI Agent Identity System
 *
 * Abstract, non-humanoid agent symbols. Each role has a unique visual language
 * that morphs and animates based on actual agent lifecycle state:
 * idle / active / searching / communicating / error / completed.
 *
 * No robot faces. No generic circles. Pure geometric identity.
 */

import { motion, useReducedMotion, type TargetAndTransition } from 'motion/react';

type AgentRole =
  | 'manager'
  | 'procurement'
  | 'negotiation'
  | 'treasury'
  | 'risk'
  | 'accounting'
  | 'recovery'
  | 'strategy'
  | 'credit'
  | 'auditor'
  | 'market_intelligence'
  | 'inventory'
  | 'supplier';

type AgentStatus = 'idle' | 'active' | 'searching' | 'communicating' | 'error' | 'completed';

interface AgentAvatarProps {
  role: AgentRole;
  status?: AgentStatus;
  size?: number;
  className?: string;
}

const roleColors: Record<AgentRole, string> = {
  manager: '#ff6a00',
  procurement: '#8cf2c8',
  negotiation: '#ffbe76',
  treasury: '#f59e0b',
  risk: '#ff4757',
  accounting: '#79a8ff',
  recovery: '#c49bea',
  strategy: '#ff9f43',
  credit: '#ff6348',
  auditor: '#ffbe76',
  market_intelligence: '#f16d6d',
  inventory: '#f2b35d',
  supplier: '#86b9f3',
};

/** Shared idle breath — slow scale pulse */
const idleBreath = {
  hidden: { scale: 1, opacity: 0.8 },
  visible: {
    scale: [1, 1.06, 1],
    opacity: [0.8, 1, 0.8],
    transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const },
  },
};

/** Activation — quick scale up and fade in */
const activate = {
  hidden: { scale: 0.6, opacity: 0 },
  visible: { scale: 1, opacity: 1, transition: { duration: 0.3, ease: 'backOut' as const } },
};

/** Error — rapid red shake */
const errorState = {
  hidden: { x: 0 },
  visible: {
    x: [0, -6, 6, -6, 6, 0],
    transition: { duration: 0.6, repeat: Infinity, ease: 'linear' as const },
  },
};

/** Completed — gentle green glow expansion */
const completedState = {
  hidden: { scale: 1, opacity: 0.8 },
  visible: {
    scale: [1, 1.15, 1],
    opacity: [0.8, 1, 0.8],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' as const },
  },
};

export function AgentAvatar({ role, status = 'idle', size = 36, className = '' }: AgentAvatarProps) {
  const reducedMotion = useReducedMotion() ?? false;
  const color = roleColors[role];

  const isActive = status === 'active' || status === 'searching' || status === 'communicating';
  // Select actual animation targets rather than nesting variant labels inside animate.
  const variants = reducedMotion
    ? { hidden: {}, visible: {} }
    : status === 'error' ? errorState : status === 'completed' ? completedState : isActive ? activate : idleBreath;

  return (
    <motion.div
      className={`agent-avatar agent-avatar-${role} ${className}`}
      style={{ width: size, height: size, position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
      animate={variants.visible}
      initial={variants.hidden}
      exit={{ opacity: 0, scale: 0.8, transition: { duration: reducedMotion ? 0 : 0.2 } }}
    >
      {renderAgent(role, size, color, status, reducedMotion)}
      {isActive && !reducedMotion && (
        <motion.div
          className="agent-activity-ring"
          animate={{
            scale: [1, 1.35, 1],
            opacity: [0.5, 0, 0.5],
            transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' as const },
          }}
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `2px solid ${color}`,
            opacity: 0.35,
            pointerEvents: 'none',
            zIndex: 0,
          }}
        />
      )}
    </motion.div>
  );
}

function renderAgent(role: AgentRole, size: number, color: string, status: AgentStatus, reducedMotion: boolean) {
  const r = size / 2;
  const cx = r;
  const cy = r;

  switch (role) {
    case 'manager':
      return <ManagerAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'procurement':
      return <ProcurementAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'negotiation':
      return <NegotiationAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'treasury':
      return <TreasuryAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'risk':
      return <RiskAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'accounting':
      return <AccountingAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'recovery':
      return <RecoveryAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'strategy':
      return <StrategyAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'credit':
      return <CreditAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'auditor':
      return <AuditorAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'market_intelligence':
      return <MarketIntelligenceAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'inventory':
      return <InventoryAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    case 'supplier':
      return <SupplierAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
    default:
      return <ManagerAgent r={r} cx={cx} cy={cy} color={color} status={status} reducedMotion={reducedMotion} />;
  }
}

/** ── Manager Agent: rotating geometric crown / command structure ── */
function ManagerAgent({ r, cx, cy, color, status, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const spin: TargetAndTransition = reducedMotion ? { rotate: 0 } : { rotate: [0, 360], transition: { duration: 6, repeat: Infinity, ease: 'linear' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <defs>
        <linearGradient id={`mg-grad-${cx}-${cy}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={color} />
          <stop offset="100%" stopColor="rgba(255,255,255,0.6)" />
        </linearGradient>
      </defs>
      {/* Crown points */}
      <motion.g animate={spin}>
        <polygon points="32,8 20,28 28,28 28,44 36,44 36,28 44,28 44,28 52,8" fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
        <circle cx="32" cy="16" r="3" fill="#fff" />
      </motion.g>
      {/* Central command orb */}
      <motion.circle cx="32" cy="32" r={status === 'active' ? 9 : 6} fill="none" stroke={color} strokeWidth="2" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Procurement Agent: searching orbital pattern with scanning arcs ── */
function ProcurementAgent({ r, color, status, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const scan: TargetAndTransition = reducedMotion ? { rotate: 0 } : { rotate: [0, 360], transition: { duration: 2.5, repeat: Infinity, ease: 'linear' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={scan}>
        <path d="M 32 16 A 16 16 0 0 1 48 32" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        <path d="M 32 48 A 16 16 0 0 1 16 32" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.5" />
        <circle cx={status === 'searching' ? 48 : 32} cy={status === 'searching' ? 32 : 16} r={status === 'searching' ? 5 : 3} fill="#fff" />
      </motion.g>
      <motion.circle cx="32" cy="32" r={5} fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="4 4" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Negotiation Agent: two intersecting forms finding equilibrium ── */
function NegotiationAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const pulse: TargetAndTransition = reducedMotion ? { scale: 1 } : { scale: [1, 1.1, 1], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={pulse}>
        <path d="M 16 24 L 32 40 L 48 24" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M 16 40 L 32 24 L 48 40" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
      </motion.g>
      <motion.circle cx="32" cy="32" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Treasury Agent: fluid vault / concentric financial rings ── */
function TreasuryAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const ringPulse: TargetAndTransition = reducedMotion ? { opacity: 1 } : { opacity: [0.4, 0.9, 0.4], transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.circle cx="32" cy="32" r={18} fill="none" stroke={color} strokeWidth="2" animate={ringPulse} />
      <motion.circle cx="32" cy="32" r={12} fill="none" stroke={color} strokeWidth="1.5" strokeOpacity="0.5" animate={{ ...ringPulse, transition: { ...ringPulse.transition, delay: reducedMotion ? 0 : 0.5 } }} />
      <motion.circle cx="32" cy="32" r={6} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Risk Agent: transforming shield with scanning lines ── */
function RiskAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const scan: TargetAndTransition = reducedMotion ? { y: 0 } : { y: [-8, 8, -8], transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <path d="M 32 12 L 14 32 L 32 52 L 50 32 Z" fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
      <motion.line x1="22" y1="22" x2="42" y2="22" stroke={color} strokeWidth="1.5" strokeOpacity="0.6" animate={scan} />
      <motion.circle cx="32" cy="32" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Accounting Agent: interlocking geometric elements representing balanced entries ── */
function AccountingAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const interlock: TargetAndTransition = reducedMotion ? { rotate: 0 } : { rotate: [0, 180, 0], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={interlock}>
        <rect x="20" y="20" width="12" height="24" fill="none" stroke={color} strokeWidth="2" rx="2" />
        <rect x="32" y="20" width="12" height="24" fill="none" stroke={color} strokeWidth="2" rx="2" strokeOpacity="0.5" />
      </motion.g>
      <circle cx="26" cy="32" r={4} fill="#fff" />
      <circle cx="38" cy="32" r={4} fill="rgba(255,255,255,0.5)" />
    </svg>
  );
}

/** ── Recovery Agent: fragmented shapes reorganizing into stable structure ── */
function RecoveryAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const reassemble: TargetAndTransition = reducedMotion ? { scale: 1 } : { scale: [0.6, 1, 0.95, 1], transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={reassemble}>
        <path d="M 20 20 L 28 28 L 20 36 Z" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        <path d="M 44 20 L 36 28 L 44 36 Z" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeOpacity="0.6" />
        <path d="M 28 36 L 36 36 L 32 44 Z" fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
      </motion.g>
      <motion.circle cx="32" cy="36" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Strategy Agent: rotating abstract data structure ── */
function StrategyAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const rotate: TargetAndTransition = reducedMotion ? { rotate: 0 } : { rotate: [0, 360], transition: { duration: 5, repeat: Infinity, ease: 'linear' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={rotate}>
        <polygon points="32,12 48,32 32,52 16,32" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        <polygon points="32,20 40,32 32,44 24,32" fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeOpacity="0.5" />
      </motion.g>
      <motion.circle cx="32" cy="32" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Credit Agent: shield with scanning lines ── */
function CreditAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const scan: TargetAndTransition = reducedMotion ? { y: 0 } : { y: [-6, 6], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <path d="M 32 14 L 18 34 L 32 54 L 46 34 Z" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      <motion.line x1="24" y1="30" x2="40" y2="30" stroke={color} strokeWidth="1.5" strokeOpacity="0.6" animate={scan} />
      <motion.circle cx="32" cy="34" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Auditor Agent: inspecting magnifying structure ── */
function AuditorAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const pulse: TargetAndTransition = reducedMotion ? { scale: 1 } : { scale: [1, 1.05, 1], transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={pulse}>
        <circle cx="32" cy="28" r={10} fill="none" stroke={color} strokeWidth="2" />
        <line x1="32" y1="38" x2="42" y2="48" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="32" cy="28" r={2} fill="#fff" />
      </motion.g>
    </svg>
  );
}

/** ── Market Intelligence Agent: broadcasting signal arcs ── */
function MarketIntelligenceAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const broadcast: TargetAndTransition = reducedMotion ? { scale: 1 } : { scale: [0.8, 1.2, 0.8], transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={broadcast}>
        <path d="M 24 32 Q 32 16 40 32" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeOpacity="0.4" />
        <path d="M 28 32 Q 32 24 36 32" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeOpacity="0.7" />
        <circle cx="32" cy="32" r={6} fill="none" stroke={color} strokeWidth="2" />
      </motion.g>
      <motion.circle cx="32" cy="32" r={3} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Inventory Agent: stacked boxes with movement indicators ── */
function InventoryAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const stack: TargetAndTransition = reducedMotion ? { y: 0 } : { y: [0, -4, 0], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={stack}>
        <rect x="22" y="20" width="20" height="10" fill="none" stroke={color} strokeWidth="2" rx="1" />
        <rect x="26" y="28" width="12" height="10" fill="none" stroke={color} strokeWidth="2" rx="1" strokeOpacity="0.5" />
        <line x1="22" y1="30" x2="42" y2="30" stroke={color} strokeWidth="1" strokeOpacity="0.4" />
      </motion.g>
      <motion.circle cx="32" cy="42" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}

/** ── Supplier Agent: factory/gate structure ── */
function SupplierAgent({ r, color, reducedMotion }: { r: number; cx: number; cy: number; color: string; status: AgentStatus; reducedMotion: boolean }) {
  const pulse: TargetAndTransition = reducedMotion ? { scale: 1 } : { scale: [1, 1.08, 1], transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' as const } };
  return (
    <svg width={r * 2} height={r * 2} viewBox="0 0 64 64" style={{ transform: `translate(${-r}px,${-r}px)` }}>
      <motion.g animate={pulse}>
        <rect x="18" y="24" width="28" height="24" fill="none" stroke={color} strokeWidth="2" rx="2" />
        <rect x="26" y="14" width="12" height="12" fill="none" stroke={color} strokeWidth="2" rx="1" />
        <line x1="24" y1="48" x2="40" y2="48" stroke={color} strokeWidth="2" strokeLinecap="round" />
      </motion.g>
      <motion.circle cx="32" cy="36" r={4} fill="#fff" animate={reducedMotion ? { scale: 1, opacity: 1 } : idleBreath.visible} />
    </svg>
  );
}