/**
 * Agentropolis — Living Economy (World Page)
 *
 * The flagship immersive economy environment. A constellation of autonomous
 * businesses suspended in a generative digital city, with animated signals
 * traveling between negotiating companies and particles representing
 * financial transactions.
 */

import { motion, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState, type PointerEvent, type RefObject } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  Bot,
  CircleDollarSign,
  Network,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  StepForward,
  Users,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

import { EconomyShell, EventRail, Money, StatusPill } from '@/components/economy/EconomyShell';
import { AgentAvatar } from '@/components/visual-identity/AgentAvatars';
import { BusinessNode } from '@/components/economy/BusinessNode';
import { AnimatedConnection } from '@/components/economy/AnimatedConnection';
import { EconomicConstellation, triggerConstellationFlash } from '@/components/ambient/EconomicConstellation';
import { ProceduralGrid } from '@/components/ambient/ProceduralGrid';
import { EconomicParticles, spawnEconomicParticle } from '@/components/ambient/EconomicParticles';
import { AgentropolisLogo } from '@/components/visual-identity/AgentropolisLogo';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import { useMotionCoordinator, useMotionEffect } from '@/components/motion/MotionEventProvider';
import { controlSimulation } from '@/lib/economy-api';
import type { EconomyBusiness, EconomyContract, EconomyAgent } from '@/types/economy';
import { AgentInspector } from '@/components/economy/AgentInspector';

function getIndustry(business: EconomyBusiness): string {
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

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return h;
}

function stablePosition(businessId: string, index: number, total: number, width: number, height: number) {
  const h = hashCode(businessId);
  const angle = (index / total) * Math.PI * 2 + (h % 100) * 0.01;
  const radius = 220 + (h % 150);
  return {
    x: width / 2 + Math.cos(angle) * radius,
    y: height / 2 + Math.sin(angle) * radius * 0.6,
  };
}

// A connection that uses element IDs instead of refs, avoiding hooks-in-loops
function SimpleConnection({
  containerId,
  fromId,
  toId,
  status,
  activity,
  curvature,
  packetInterval,
}: {
  containerId: string;
  fromId: string;
  toId: string;
  status: 'negotiating' | 'active' | 'disrupted' | 'defaulted' | 'forming' | 'dissolving';
  activity?: number;
  curvature?: number;
  packetInterval?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fromRef = useRef<HTMLDivElement>(null);
  const toRef = useRef<HTMLDivElement>(null);

  // Sync refs to elements by ID on each render
  useEffect(() => {
    containerRef.current = document.getElementById(containerId) ?? null;
    fromRef.current = document.getElementById(fromId) ?? null;
    toRef.current = document.getElementById(toId) ?? null;
  }, [containerId, fromId, toId]);

  if (!containerRef.current || !fromRef.current || !toRef.current) return null;

  return (
    <AnimatedConnection
      containerRef={containerRef as unknown as RefObject<HTMLElement>}
      fromRef={fromRef as unknown as RefObject<HTMLElement>}
      toRef={toRef as unknown as RefObject<HTMLElement>}
      status={status}
      activity={activity}
      curvature={curvature}
      packetInterval={packetInterval}
    />
  );
}

export function WorldPage() {
  const { summary, events, loading, connected, error, refresh } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const { coordinator } = useMotionCoordinator();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<EconomyAgent | null>(null);
  const [shake, setShake] = useState(0);
  const [flash, setFlash] = useState(0);
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const canvasRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, RefObject<HTMLElement>>>(new Map());

  const dragging = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);

  const businesses = summary?.businesses ?? [];
  const contracts = summary?.contracts ?? [];
  const agents = summary?.agent_runtime?.agents ?? [];
  const buyer = businesses.find((b) => b.role === 'buyer');

  const visibleBusinesses = businesses.filter((b) => b.active !== false);
  const totalCash = businesses.reduce((sum, b) => sum + b.cash_cents, 0);
  const totalReserve = businesses.reduce((sum, b) => sum + b.reserve_cents, 0);
  const computedHealth = totalReserve > 0 ? Math.min(1, totalCash / Math.max(totalReserve, 1)) : 0.7;

  const settled = contracts.filter(
    (c) => ['confirmed', 'reconciled', 'paid'].includes((c.payment_state ?? c.status ?? '').toLowerCase()),
  ).length;
  const activeContracts = contracts.filter(
    (c) => !['confirmed', 'reconciled', 'paid', 'defaulted', 'cancelled'].includes((c.payment_state ?? c.status ?? '').toLowerCase()),
  ).length;

  // Ensure stable refs exist for every business
  useEffect(() => {
    visibleBusinesses.forEach((b) => {
      if (!nodeRefs.current.has(b.business_id)) {
        nodeRefs.current.set(b.business_id, { current: null });
      }
    });
  }, [visibleBusinesses]);

  // Stable positions
  const positions = new Map<string, { x: number; y: number }>();
  visibleBusinesses.forEach((b, i) => {
    positions.set(b.business_id, stablePosition(b.business_id, i, visibleBusinesses.length, 900, 600));
  });

  // Connections from contracts - use IDs instead of refs to avoid hooks-in-loops
  const relationshipConnections = contracts.map((c) => {
    const status = (c.payment_state ?? c.status ?? 'active').toLowerCase();
    const connStatus =
      status === 'defaulted' || status === 'cancelled' ? 'defaulted' :
      status === 'pending' || status === 'proposed' ? 'forming' :
      status === 'reconciled' || status === 'confirmed' ? 'active' : 'active';
    return {
      contract: c,
      from: c.buyer_id,
      to: c.supplier_id,
      status: connStatus as any,
      id: c.contract_id,
      fromElId: `node-${c.buyer_id}`,
      toElId: `node-${c.supplier_id}`,
    };
  });

  // ── Motion coordinator subscriptions ──
  useMotionEffect({
    id: 'payment-particle-flow',
    name: 'Payment confirmation particle flow',
    layer: 'data-driven',
    eventTypes: ['PaymentConfirmed', 'PaymentRecorded'],
    handler: (event) => {
      const buyerId = event.business_id;
      const contract = contracts.find((c) => c.contract_id === event.deal_id);
      const supplierId = contract?.supplier_id;
      if (!buyerId || !supplierId || !canvasRef.current) return;

      const fromRef = nodeRefs.current.get(buyerId);
      const toRef = nodeRefs.current.get(supplierId);
      if (!fromRef?.current || !toRef?.current) return;

      const containerRect = canvasRef.current.getBoundingClientRect();
      const fromRect = fromRef.current.getBoundingClientRect();
      const toRect = toRef.current.getBoundingClientRect();

      spawnEconomicParticle({
        fromX: fromRect.left - containerRect.left + fromRect.width / 2,
        fromY: fromRect.top - containerRect.top + fromRect.height / 2,
        toX: toRect.left - containerRect.left + toRect.width / 2,
        toY: toRect.top - containerRect.top + toRect.height / 2,
        type: 'payment',
        amountCents: Number(event.payload?.amount_cents ?? 0),
      });

      setFlash((f) => f + 1);
      triggerConstellationFlash();
    },
    cost: 'medium',
  });

  useMotionEffect({
    id: 'supplier-defaulted',
    name: 'Supplier default visual',
    layer: 'data-driven',
    eventTypes: ['SupplierDefaulted', 'DeliveryFailed'],
    handler: () => {
      setShake((s) => s + 1);
      setFlash((f) => f + 1);
      triggerConstellationFlash();
    },
    cost: 'medium',
  });

  useMotionEffect({
    id: 'shock-flash',
    name: 'Economic shock cinematic flash',
    layer: 'cinematic',
    eventTypes: ['ShockInjected'],
    handler: () => {
      setFlash((f) => f + 1);
      setShake((s) => s + 1);
      triggerConstellationFlash();
    },
    cost: 'low',
  });

  async function control(action: 'tick' | 'pause' | 'resume' | 'speed', speed?: number) {
    setBusy(true);
    setNotice('');
    try {
      await controlSimulation(action, speed);
      await refresh();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Control failed');
    } finally {
      setBusy(false);
    }
  }

  function startPan(e: PointerEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement).closest('button,a,input,.business-node')) return;
    dragging.current = { x: e.clientX, y: e.clientY, startX: pan.x, startY: pan.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: PointerEvent<HTMLDivElement>) {
    setCursor({ x: e.clientX, y: e.clientY });
    if (dragging.current) {
      setPan({
        x: dragging.current.startX + e.clientX - dragging.current.x,
        y: dragging.current.startY + e.clientY - dragging.current.y,
      });
    }
  }

  const graphWidth = 900;
  const graphHeight = 700;

  const containerStyle: React.CSSProperties = {
    width: graphWidth,
    height: graphHeight,
    position: 'relative',
    transform: `translate(${pan.x}px,${pan.y}px) scale(${zoom})`,
    transformOrigin: 'center center',
    willChange: 'transform',
  };

  return (
    <EconomyShell
      eyebrow="The World / 01"
      title="A living economy, moving in real time."
      connected={connected}
      actions={
        <>
          <Link className="economy-button economy-button-small economy-button-secondary" to="/economy/businesses">
            <Plus size={14} /> Business
          </Link>
          <Link className="economy-text-link" to="/economy/scenarios">
            Stress-test the economy <ArrowUpRight size={14} />
          </Link>
        </>
      }
    >
      {(error || notice) && (
        <div className="economy-notice" role="status">{error || notice}</div>
      )}

      {/* ── Layer 1 & 5: Ambient + Generative background ── */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <EconomicConstellation particleCount={45} connectionDistance={200} />
        <ProceduralGrid marketHealth={computedHealth} cursorX={cursor.x} cursorY={cursor.y} />
      </div>

      <section className="economy-hero-grid">
        <div className="economy-hero-copy">
          <div className="economy-kicker">
            <span className="pulse-ring" /> Autonomous business network
          </div>
          <h2>
            Watch the agents <AgentropolisLogo size={20} style={{ verticalAlign: 'middle', marginLeft: 8 }} />
          </h2>
          <p>
            Businesses discover each other, negotiate, and protect their cash. Follow the decisions and
            inspect the evidence behind every move.
          </p>
          <div className="economy-hero-actions">
            <Link className="economy-button economy-button-primary" to="/economy/negotiations">
              Open negotiation room <ArrowUpRight size={15} />
            </Link>
            <Link className="economy-text-link" to="/economy/scenarios">
              Stress-test the economy <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>

        <div className="world-signal-card">
          <div className="world-signal-top">
            <span>ECONOMY CLOCK</span>
            <StatusPill tone={summary?.clock_control?.paused ? 'warn' : 'good'}>
              {summary?.clock_control?.paused ? 'paused' : summary?.status ?? 'loading'}
            </StatusPill>
          </div>
          <div className="world-signal-number">
            D{summary?.clock_control?.day ?? '—'}<span> / TICK {summary?.clock_control?.tick ?? '—'}</span>
          </div>
          <div className="world-signal-chart">
            <div className="chart-axis">
              <span>{buyer?.name ?? 'Buyer'} · ledger cash</span>
              <span>{businesses.length} businesses</span>
            </div>
            <svg viewBox="0 0 420 92" role="img" aria-label="Buyer cash balance from ledger postings">
              <polyline points="" fill="none" stroke="#8cf2c8" strokeWidth="2" />
            </svg>
          </div>
          <div className="clock-controls">
            <button
              className="economy-button economy-button-small economy-button-secondary"
              disabled={busy || !summary}
              onClick={() => void control(summary?.clock_control?.paused ? 'resume' : 'pause')}
            >
              {summary?.clock_control?.paused ? <Play size={14} /> : <Pause size={14} />}
              {summary?.clock_control?.paused ? ' Resume' : ' Pause'}
            </button>
            <button
              className="economy-button economy-button-small economy-button-secondary"
              disabled={busy || !summary}
              onClick={() => void control('tick')}
            >
              <StepForward size={14} /> Advance tick
            </button>
            <label style={{ fontSize: 10, color: '#666', marginLeft: 8, fontFamily: 'monospace' }}>
              Speed
              <select
                value={summary?.clock_control?.speed ?? 1}
                onChange={(e) => void control('speed', parseFloat(e.target.value))}
                disabled={busy || !summary}
                style={{
                  background: 'transparent',
                  border: '1px solid #333',
                  color: '#ededed',
                  padding: '4px 6px',
                  fontSize: 10,
                  fontFamily: 'monospace',
                  borderRadius: 4,
                }}
              >
                <option value="0.25">0.25×</option>
                <option value="1">1×</option>
                <option value="2">2×</option>
                <option value="4">4×</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      {/* ── Stats ── */}
      <motion.div
        className="economy-stat-grid"
        initial={reducedMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.4 }}
      >
        {[
          { label: 'Operating businesses', value: businesses.filter((b) => b.active).length, icon: Users, note: `${businesses.length} registered` },
          { label: 'Network liquidity', value: totalCash, money: true, icon: CircleDollarSign, note: 'simulated account balances' },
          { label: 'Contracts active', value: activeContracts, icon: Network, note: `${contracts.length} total` },
          { label: 'Contracts settled', value: settled, icon: ShieldCheck, note: 'payments confirmed' },
        ].map(({ label, value, icon: Icon, note, money }) => (
          <div className="economy-stat-card" key={label}>
            <div className="stat-card-icon"><Icon size={16} /></div>
            <div className="economy-stat-label">{label}</div>
            <div className="economy-stat-value">{money ? <Money cents={Number(value)} /> : value}</div>
            <div className="economy-stat-note">{note}</div>
          </div>
        ))}
      </motion.div>

      {/* ── Living Economy Map ── */}
      <section className="economy-panel agent-network-panel">
        <div className="economy-panel-heading">
          <div>
            <span className="economy-overline">LIVING ECONOMY</span>
            <h3>Who is trading with whom</h3>
          </div>
          <span className="economy-panel-meta">
            {visibleBusinesses.length} businesses · {relationshipConnections.length} relationships
          </span>
        </div>

        <div className="map-toolbar">
          <label className="search-field">
            <Search size={14} />
            <input aria-label="Filter businesses" placeholder="Find business or industry…" value="" onChange={() => {}} />
          </label>
          <div>
            <button className="economy-icon-button" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}>
              <ZoomOut size={16} />
            </button>
            <button className="economy-icon-button" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(2, z + 0.15))}>
              <ZoomIn size={16} />
            </button>
            <button className="economy-icon-button" aria-label="Reset map view" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>
              <RotateCcw size={14} />
            </button>
          </div>
        </div>

        <div
          id="economy-map-container"
          ref={canvasRef}
          className="world-map interactive-map"
          onPointerDown={startPan}
          onPointerMove={handlePointerMove}
          onPointerUp={() => (dragging.current = null)}
          onPointerCancel={() => (dragging.current = null)}
          style={containerStyle}
        >
          {/* Animated connections (drawn first, behind nodes) */}
          {relationshipConnections.map((conn) => (
            <SimpleConnection
              key={conn.id}
              containerId="economy-map-container"
              fromId={conn.fromElId}
              toId={conn.toElId}
              status={conn.status}
              activity={conn.status === 'active' ? 0.7 : 0.4}
              curvature={80}
              packetInterval={reducedMotion ? 0 : 1000}
            />
          ))}

          {/* Business nodes */}
          {visibleBusinesses.map((business) => {
            const pos = positions.get(business.business_id);
            if (!pos) return null;
            const isSelected = selectedId === business.business_id;
            const isDisrupted = contracts.some(
              (c) =>
                (c.buyer_id === business.business_id || c.supplier_id === business.business_id) &&
                (c.payment_state === 'defaulted' || c.payment_state === 'cancelled'),
            );
            const isNegotiating = contracts.some(
              (c) =>
                (c.buyer_id === business.business_id || c.supplier_id === business.business_id) &&
                (c.payment_state === 'pending' || c.payment_state === 'proposed'),
            );

            return (
              <div
                id={`node-${business.business_id}`}
                key={business.business_id}
                style={{
                  position: 'absolute',
                  left: pos.x,
                  top: pos.y,
                  zIndex: isSelected ? 10 : 1,
                }}
              >
                <BusinessNode
                  ref={(el) => {
                    const ref = nodeRefs.current.get(business.business_id);
                    if (ref) ref.current = el as unknown as HTMLElement;
                  }}
                  business={business}
                  x={0}
                  y={0}
                  state={isDisrupted ? 'disrupted' : isNegotiating ? 'negotiating' : 'active'}
                  selected={isSelected}
                  size={isSelected ? 56 : 44}
                  onClick={() => setSelectedId(business.business_id)}
                />
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Agent teams panel ── */}
      <section className="economy-panel agent-network-panel">
        <div className="economy-panel-heading">
          <div>
            <span className="economy-overline">AGENT TEAMS</span>
            <h3>Decisions have owners</h3>
          </div>
          <span className="economy-panel-meta">
            <Bot size={14} /> {agents.length} deployed roles
          </span>
        </div>
        <div className="agent-team-grid">
          {agents.slice(0, 12).map((agent) => (
            <button
              className="agent-team-card"
              key={agent.agent_id}
              onClick={() => setSelectedAgent(agent)}
              aria-label={`Inspect ${agent.role} agent`}
            >
              <div className="agent-team-card-top">
                <span className="agent-role-icon">
                  <AgentAvatar role={agent.role as any} status={agent.status as any} size={20} />
                </span>
                <span className={`agent-status agent-status-${agent.status}`}>{agent.status}</span>
              </div>
              <strong>{agent.role}</strong>
              <small>{agent.handled_messages} msgs · {agent.decisions} decisions</small>
            </button>
          ))}
        </div>
        <div className="agent-runtime-footer">
          <span>{summary?.agent_runtime?.tasks.length ?? 0} tasks</span>
          <span>{summary?.agent_runtime?.messages.length ?? 0} messages</span>
          <span>{summary?.agent_runtime?.transport?.mode ?? '—'} transport</span>
        </div>
      </section>

      <AgentInspector agent={selectedAgent} summary={summary} onClose={() => setSelectedAgent(null)} />
    </EconomyShell>
  );
}