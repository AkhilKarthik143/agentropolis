import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { AlertOctagon, Flame, Play, RotateCcw, Siren, TriangleAlert, Zap } from 'lucide-react';
import { useState } from 'react';
import { EconomyShell, EventRail, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import { replayEconomy, triggerShock } from '@/lib/economy-api';

const shocks = [
  { id: 'supplier_bankruptcy', label: 'Supplier bankruptcy', detail: 'A primary supplier disappears mid-deal.', icon: AlertOctagon, tone: 'red' },
  { id: 'demand_spike', label: 'Demand spike', detail: 'Unexpected demand burns through inventory.', icon: Flame, tone: 'orange' },
  { id: 'shortage', label: 'Supply shortage', detail: 'The broker has to source a scarce input.', icon: TriangleAlert, tone: 'yellow' },
  { id: 'suspicious_invoice', label: 'Suspicious invoice', detail: 'Risk agent pauses an anomalous charge.', icon: Siren, tone: 'purple' },
  { id: 'failed_payment', label: 'Failed payment', detail: 'Treasury retries without double-posting.', icon: RotateCcw, tone: 'blue' },
  { id: 'liquidity_crisis', label: 'Liquidity crisis', detail: 'Reserve policy tightens in response.', icon: Zap, tone: 'green' },
];

export function ScenariosPage() {
  const { events, connected, refresh } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const [running, setRunning] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const runShock = async (id: string) => { setRunning(id); setMessage(''); try { const result = await triggerShock(id); setMessage(`${id.replaceAll('_', ' ')} injected · agents are replanning`); await refresh(); return result; } catch (error) { setMessage(error instanceof Error ? error.message : 'Shock failed'); } finally { setRunning(null); } };
  const replay = async () => { const result = await replayEconomy(); setMessage(`Replay verified · ${String(result.event_count ?? '—')} events in sequence`); };
  const latestShockIndex = [...events].reverse().findIndex((event) => event.type === 'ShockInjected');
  const latestShock = latestShockIndex >= 0 ? events[events.length - 1 - latestShockIndex] : undefined;
  const shockWindow = latestShock ? events.filter((event) => event.seq >= latestShock.seq) : [];
  const supplierShock = latestShock?.payload.shock_type === 'supplier_bankruptcy';
  const recoverySteps = supplierShock ? [
    { label: 'Node failed', types: ['SupplierDefaulted', 'SUPPLIER_BANKRUPT'] },
    { label: 'Connections alerted', types: ['DELIVERY_AT_RISK', 'RECOVERY_STARTED'] },
    { label: 'Agents re-source', types: ['ReplanStarted', 'RecoveryPlanProposed'] },
    { label: 'Inventory recovered', types: ['REPLACEMENT_OFFER_RECEIVED', 'REPLACEMENT_APPROVED', 'INVENTORY_RECOVERED'] },
  ] : [
    { label: 'Shock injected', types: ['ShockInjected'] },
    { label: 'Risk surfaced', types: ['ACTION_BLOCKED', 'SUPPLIER_BLOCKED', 'ReplanStarted'] },
    { label: 'Agents re-plan', types: ['ReplanStarted', 'OfferCreated', 'CounterOfferReceived'] },
    { label: 'State confirmed', types: ['ContractAccepted', 'PaymentRecorded', 'LedgerPosted', 'INVENTORY_RECOVERED'] },
  ];
  const recoveryStage = recoverySteps.reduce((stage, step, index) => shockWindow.some((event) => step.types.includes(event.type)) ? Math.max(stage, index) : stage, latestShock ? 0 : -1);
  return <EconomyShell eyebrow="Scenario engine / 04" title="Find the fault line." connected={connected} actions={<button className="economy-button economy-button-small economy-button-secondary" onClick={() => void replay()}><Play size={13} /> Replay event log</button>}>
    <section className="scenario-intro"><div><div className="economy-kicker"><span className="pulse-ring pulse-ring-hot" /> Deterministic disruption lab</div><p>Inject a shock. The agents must re-source, renegotiate, protect the reserve, or escalate. The engine owns the outcome.</p></div><AnimatePresence initial={false} mode="wait">{message && <motion.div initial={reducedMotion ? false : { opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={reducedMotion ? undefined : { opacity: 0, y: -6 }}><StatusPill tone="good">{message}</StatusPill></motion.div>}</AnimatePresence></section>
    <section className="shock-grid">{shocks.map(({ id, label, detail, icon: Icon, tone }) => <motion.button className={`shock-card shock-${tone}`} key={id} onClick={() => void runShock(id)} disabled={running !== null} whileHover={reducedMotion ? undefined : { y: -3 }} whileTap={reducedMotion ? undefined : { scale: 0.99 }} transition={{ duration: reducedMotion ? 0 : 0.14 }}><div className="shock-card-top"><div className="shock-icon"><Icon size={17} /></div><span className="shock-run">{running === id ? 'running…' : 'inject'} <Play size={11} /></span></div><b>{label}</b><span>{detail}</span><div className="shock-card-footer"><span>STATE MUTATION</span><span>→</span></div></motion.button>)}</section>
    <AnimatePresence initial={false}>{latestShock && <motion.section className="economy-panel shock-live-trace" initial={reducedMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reducedMotion ? undefined : { opacity: 0, y: 12 }} transition={{ duration: reducedMotion ? 0 : 0.3 }}><div className="economy-panel-heading"><div><span className="economy-overline">LIVE CAUSE → EFFECT</span><h3>{String(latestShock.payload.shock_type ?? 'shock').replaceAll('_', ' ')} propagation</h3></div><StatusPill tone={recoveryStage >= recoverySteps.length - 1 ? 'good' : 'warn'}>{recoveryStage >= recoverySteps.length - 1 ? 'recovered' : 'in flight'}</StatusPill></div><div className="shock-trace-steps">{recoverySteps.map((step, index) => <motion.div className={`shock-trace-step ${index <= recoveryStage ? 'complete' : ''} ${index === recoveryStage ? 'current' : ''}`} key={step.label} initial={reducedMotion ? false : { opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: reducedMotion ? 0 : index * 0.06, duration: reducedMotion ? 0 : 0.2 }}><div className="shock-trace-marker">{String(index + 1).padStart(2, '0')}</div><div><b>{step.label}</b><small>{index <= recoveryStage ? 'confirmed by event stream' : 'waiting for backend event'}</small></div></motion.div>)}</div><div className="shock-trace-foot">Latest event <b>{shockWindow.at(-1)?.type ?? latestShock.type}</b> · seq {shockWindow.at(-1)?.seq ?? latestShock.seq}</div></motion.section>}</AnimatePresence>
    <section className="scenario-lower-grid"><div className="economy-panel replay-panel"><div className="economy-panel-heading"><div><span className="economy-overline">REPLAY + AUDIT</span><h3>Everything has a receipt</h3></div><StatusPill tone="good">append-only</StatusPill></div><div className="replay-card"><div className="replay-number">{events.length}</div><div><b>Events captured</b><span>Monotonic sequence IDs make every decision replayable.</span></div><button className="economy-button economy-button-small economy-button-primary" onClick={() => void replay()}>Verify replay <RotateCcw size={13} /></button></div><div className="audit-note">Replay uses the seeded clock, deterministic policy checks, and recorded proposal payloads. No UI animation is standing in for state.</div></div><div className="economy-panel"><div className="economy-panel-heading"><div><span className="economy-overline">AUDIT TRAIL</span><h3>Last decisions</h3></div><span className="economy-panel-meta">ordered by seq</span></div><EventRail events={events} limit={12} /></div></section>
  </EconomyShell>;
}

