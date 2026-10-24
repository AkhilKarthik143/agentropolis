/**
 * Agentropolis — Cinematic Shock Overlay
 *
 * Full-screen, event-driven cinematic sequences for major economic events:
 * - Supplier bankruptcy: node fracture, connection disruption, alert wave, recovery
 * - Demand spike: expanding energy wave, intensifying activity, bottlenecks
 * - Liquidity crisis: contracting paths, treasury warning, interrupted payments
 * - Fraud detection: suspicious transaction isolation, risk agent activation, rejection
 *
 * These are choreographed visual experiences, not pre-recorded fakes.
 * Triggered by real backend ShockInjected events.
 */

import { AnimatePresence, motion, useReducedMotion, useSpring, useTransform } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { AlertOctagon, Flame, Zap, ShieldAlert, RotateCcw, Users, Network, Truck } from 'lucide-react';
import { triggerConstellationFlash } from '@/components/ambient/EconomicConstellation';
import { spawnEconomicParticle } from '@/components/ambient/EconomicParticles';
import { AgentAvatar } from '@/components/visual-identity/AgentAvatars';

type ShockType = 'supplier_bankruptcy' | 'demand_spike' | 'liquidity_crisis' | 'fraud_detection' | 'recovery';

interface CinematicShockOverlayProps {
  shockType: ShockType | null;
  supplierId?: string | null;
  onClose: () => void;
  recoveryProgress?: number; // 0-1
}

const shockConfig: Record<ShockType, { label: string; icon: any; color: string; duration: number }> = {
  supplier_bankruptcy: { label: 'Supplier Bankruptcy', icon: AlertOctagon, color: '#ff4757', duration: 5 },
  demand_spike: { label: 'Demand Spike', icon: Flame, color: '#ffbe76', duration: 4 },
  liquidity_crisis: { label: 'Liquidity Crisis', icon: Zap, color: '#f59e0b', duration: 4 },
  fraud_detection: { label: 'Fraud Detection', icon: ShieldAlert, color: '#c49bea', duration: 4 },
  recovery: { label: 'Economic Recovery', icon: Network, color: '#8cf2c8', duration: 3 },
};

export function CinematicShockOverlay({ shockType, supplierId, onClose, recoveryProgress = 0 }: CinematicShockOverlayProps) {
  const reducedMotion = useReducedMotion();
  const [stage, setStage] = useState(0);
  const [shakeIntensity, setShakeIntensity] = useState(0);
  const [waveRadius, setWaveRadius] = useState(0);
  const [waveOpacity, setWaveOpacity] = useState(0);
  const [particleBurst, setParticleBurst] = useState(0);

  const config = shockConfig[shockType ?? 'recovery'];
  const canvasRef = useRef<HTMLDivElement>(null);

  // ── Stage choreography ──
  useEffect(() => {
    if (!shockType || reducedMotion) {
      setStage(0);
      return;
    }

    triggerConstellationFlash();

    let t: number | null = null;
    const sequence: Array<() => void> = [];

    if (shockType === 'supplier_bankruptcy') {
      sequence.push(
        () => setStage(1), // t+0: warning signals
        () => setShakeIntensity(1), // t+0.5: shake begins
        () => setStage(2), // t+1.0: fracture
        () => setWaveRadius(400), // t+1.5: alert wave
        () => setWaveOpacity(0.4),
        () => setParticleBurst(1), // t+2.0: particle burst
        () => setStage(3), // t+3.0: recovery agents activate
        () => setShakeIntensity(0),
        () => setWaveRadius(0),
        () => setWaveOpacity(0),
      );
    } else if (shockType === 'demand_spike') {
      sequence.push(
        () => setStage(1),
        () => setWaveRadius(300),
        () => setWaveOpacity(0.3),
        () => setStage(2),
        () => setParticleBurst(1),
        () => setStage(3),
      );
    } else if (shockType === 'liquidity_crisis') {
      sequence.push(
        () => setStage(1),
        () => setShakeIntensity(1),
        () => setStage(2),
        () => setWaveRadius(350),
        () => setWaveOpacity(0.35),
        () => setStage(3),
      );
    } else if (shockType === 'fraud_detection') {
      sequence.push(
        () => setStage(1),
        () => setShakeIntensity(1),
        () => setStage(2),
        () => setParticleBurst(1),
        () => setStage(3),
      );
    }

    let step = 0;
    const run = () => {
      if (step < sequence.length) {
        sequence[step]();
        step++;
        t = window.setTimeout(run, 800);
      }
    };
    t = window.setTimeout(run, 100);
    return () => { if (t) window.clearTimeout(t); };
  }, [shockType, reducedMotion]);

  // ── Spawn particles on burst ──
  useEffect(() => {
    if (!particleBurst || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    for (let i = 0; i < 20; i++) {
      const angle = (i / 20) * Math.PI * 2;
      const distance = 100 + Math.random() * 150;
      setTimeout(() => {
        spawnEconomicParticle({
          fromX: centerX,
          fromY: centerY,
          toX: centerX + Math.cos(angle) * distance,
          toY: centerY + Math.sin(angle) * distance,
          type: shockType === 'fraud_detection' ? 'alert' : 'payment',
          amountCents: 1000,
        });
      }, i * 40);
    }
  }, [particleBurst, shockType, canvasRef]);

  if (!shockType || reducedMotion) return null;

  return (
    <div className="cinematic-overlay" ref={canvasRef}>
      {/* Background dim */}
      <motion.div
        className="cinematic-backdrop"
        animate={{ opacity: [0, 0.85, 0.85, 0] }}
        transition={{ duration: config.duration, times: [0, 0.1, 0.9, 1] }}
      />

      {/* Shock wave */}
      <motion.div
        className="cinematic-wave"
        animate={{
          scale: [0, waveRadius / 50, 0],
          opacity: [0, waveOpacity, 0],
        }}
        transition={{ duration: 2, repeat: stage > 0 ? Infinity : 0, ease: 'easeInOut' }}
        style={{
          backgroundColor: config.color,
          mixBlendMode: 'screen',
        }}
      />

      {/* Main shock content */}
      <motion.div
        className="cinematic-content"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: reducedMotion ? 0 : 0.4 }}
        style={{
          animation: shakeIntensity > 0 ? 'cinematic-shake 0.4s ease-in-out infinite' : 'none',
        }}
      >
        <div className="cinematic-header">
          <div className="cinematic-icon" style={{ background: `rgba(${hexToRgb(config.color)}, 0.15)`, color: config.color }}>
            <config.icon size={28} />
          </div>
          <div>
            <h2 style={{ color: config.color, margin: 0 }}>{config.label}</h2>
            <p style={{ opacity: 0.7, margin: 0, fontSize: 14 }}>{shockStageLabel(stage, shockType)}</p>
          </div>
        </div>

        {renderShockVisuals(shockType, stage, recoveryProgress)}

        <div className="cinematic-progress">
          <motion.div
            className="cinematic-progress-bar"
            animate={{ width: `${(stage / 4) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        <button className="cinematic-close" onClick={onClose}>
          <Users size={16} />
        </button>
      </motion.div>

      <AnimatePresence>
        {stage > 0 && (
          <motion.div
            className="cinematic-afterglow"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.3 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              boxShadow: `0 0 60px ${config.color}`,
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '255, 255, 255';
}

function shockStageLabel(stage: number, type: ShockType): string {
  const labels: Record<ShockType, string[]> = {
    supplier_bankruptcy: [
      'Awaiting trigger',
      'Warning signals detected',
      'Supplier node fractured',
      'Alert wave propagating',
      'Recovery agents activated',
    ],
    demand_spike: [
      'Awaiting trigger',
      'Demand wave detected',
      'Energy expanding through network',
      'Supplier activity intensifying',
      'Market stabilizing',
    ],
    liquidity_crisis: [
      'Awaiting trigger',
      'Liquidity stress detected',
      'Cash paths contracting',
      'Reserve threshold breached',
      'Recovery pathways opening',
    ],
    fraud_detection: [
      'Awaiting trigger',
      'Suspicious transaction isolated',
      'Risk agents activated',
      'Validation checks in progress',
      'Transaction resolved',
    ],
    recovery: [
      'Recovery initiated',
      'Alternative suppliers sourced',
      'New contracts forming',
      'Economy stabilizing',
    ],
  };
  return labels[type][Math.min(stage, labels[type].length - 1)] ?? '';
}

function renderShockVisuals(type: ShockType, stage: number, recoveryProgress: number) {
  const reduced = false;

  if (type === 'supplier_bankruptcy') {
    return (
      <div className="shock-visuals bankruptcy">
        {/* Fracturing supplier node */}
        <motion.div
          className="fractured-node"
          animate={{
            scale: stage >= 2 ? [1, 0.6, 0.8] : 1,
            rotate: stage >= 2 ? [0, -10, 10, 0] : 0,
            opacity: stage >= 2 ? 0.6 : 1,
          }}
          transition={{ duration: 0.8 }}
        >
          <svg width="64" height="64" viewBox="0 0 64 64">
            <rect x="18" y="18" width="28" height="28" rx="4" fill="none" stroke="#ff4757" strokeWidth="3" />
            <line x1="18" y1="18" x2="46" y2="46" stroke="#ff4757" strokeWidth="2" strokeOpacity="0.5" />
            <line x1="46" y1="18" x2="18" y2="46" stroke="#ff4757" strokeWidth="2" strokeOpacity="0.5" />
            <circle cx="32" cy="32" r="8" fill="#ff4757" opacity={stage >= 2 ? 0.3 : 1} />
          </svg>
        </motion.div>

        {/* Recovery agents */}
        {stage >= 3 && (
          <div className="recovery-agents">
            <span>Recovery agents: </span>
            <AgentAvatar role="recovery" status="active" size={24} />
            <AgentAvatar role="procurement" status="searching" size={24} />
            <AgentAvatar role="negotiation" status="communicating" size={24} />
            <span>sourcing replacements…</span>
          </div>
        )}

        {/* Progress */}
        {recoveryProgress > 0 && (
          <div className="recovery-progress">
            <span>Recovery: {Math.round(recoveryProgress * 100)}%</span>
          </div>
        )}
      </div>
    );
  }

  if (type === 'demand_spike') {
    return (
      <div className="shock-visuals demand">
        <div className="energy-wave">
          <motion.div
            className="wave-ring"
            animate={{
              scale: [1, 2.5, 1],
              opacity: [0.6, 0, 0.6],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="wave-ring"
            animate={{
              scale: [1, 2, 1],
              opacity: [0.4, 0, 0.4],
            }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
          />
        </div>
        <div className="demand-indicator">
          <Truck size={24} style={{ color: '#ffbe76', animation: 'pulse 1.5s infinite' }} />
          <span>Demand propagating through supply chain</span>
        </div>
      </div>
    );
  }

  if (type === 'liquidity_crisis') {
    return (
      <div className="shock-visuals liquidity">
        <div className="contracting-path">
          <motion.div
            className="path-segment"
            animate={{ width: [100, 40, 100] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="path-segment"
            animate={{ width: [100, 30, 100] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
          />
          <motion.div
            className="path-segment"
            animate={{ width: [100, 50, 100] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
          />
        </div>
        <div className="liquidity-warning">
          <Zap size={24} style={{ color: '#f59e0b', animation: 'pulse 1s infinite' }} />
          <span>Reserve threshold breached — cash paths contracting</span>
        </div>
      </div>
    );
  }

  if (type === 'fraud_detection') {
    return (
      <div className="shock-visuals fraud">
        <div className="isolated-transaction">
          <motion.div
            className="transaction-node"
            animate={{
              scale: [1, 1.3, 1],
              borderColor: ['#ededed', '#c49bea', '#ededed'],
            }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          >
            <ShieldAlert size={20} style={{ color: '#c49bea' }} />
          </motion.div>
          <div className="risk-agents">
            <AgentAvatar role="risk" status="active" size={24} />
            <AgentAvatar role="auditor" status="active" size={24} />
            <span>Risk agents validating…</span>
          </div>
        </div>
        <div className="fraud-result">
          <span>Transaction isolated · Authorization paused</span>
        </div>
      </div>
    );
  }

  // Recovery
  return (
    <div className="shock-visuals recovery">
      <div className="rebuilding-connections">
        <Network size={24} style={{ color: '#8cf2c8', animation: 'pulse 2s infinite' }} />
        <span>New stable connections forming</span>
      </div>
      <div className="recovery-meter">
        <span>Economy recovering: {Math.round(recoveryProgress * 100)}%</span>
      </div>
    </div>
  );
}