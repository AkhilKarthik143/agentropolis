import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ArrowUpRight, Boxes, CircleDollarSign, Network, ShieldCheck, Users, X } from 'lucide-react';
import { useRef, useState, type Dispatch, type MouseEvent, type RefCallback, type SetStateAction } from 'react';
import { Link } from 'react-router-dom';
import { AnimatedGroup } from '@/components/motion/AnimatedGroup';
import { MagicAnimatedBeam } from '@/components/motion/MagicAnimatedBeam';
import { ReactBitsBlurText } from '@/components/motion/ReactBitsBlurText';
import { EconomyShell, EventRail, Money, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import type { EconomyBusiness, EconomyEvent } from '@/types/economy';

const nodePositions = [[18, 48], [48, 22], [74, 47], [37, 77], [77, 78], [58, 66], [20, 78]];
const flowEvents = new Set(['OfferCreated', 'CounterOfferReceived', 'ContractAccepted', 'PaymentAuthorized', 'PaymentRecorded', 'LedgerPosted', 'REPLACEMENT_OFFER_RECEIVED', 'INVENTORY_RECOVERED']);
const shockEvents = new Set(['ShockInjected', 'SupplierDefaulted', 'SUPPLIER_BANKRUPT', 'DELIVERY_AT_RISK', 'RECOVERY_STARTED', 'ReplanStarted', 'RecoveryPlanProposed', 'REPLACEMENT_OFFER_RECEIVED', 'INVENTORY_RECOVERED']);
const MotionLink = motion.create(Link);

function eventBusinessIds(event: EconomyEvent | undefined) {
  if (!event) return new Set<string>();
  const payload = event.payload ?? {};
  return new Set([event.business_id, String(payload.business_id ?? ''), String(payload.supplier_id ?? ''), String(payload.failed_supplier ?? ''), String(payload.replacement_supplier ?? '')].filter(Boolean));
}

type NodeProps = { business: EconomyBusiness; index: number; active: boolean; disrupted: boolean; reducedMotion: boolean; onSelect: Dispatch<SetStateAction<EconomyBusiness | null>>; nodeRef?: RefCallback<HTMLAnchorElement> };

function Node({ business, index, active, disrupted, reducedMotion, onSelect, nodeRef }: NodeProps) {
  const [left, top] = nodePositions[index % nodePositions.length];
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onSelect(business);
  };
  return <MotionLink ref={nodeRef} className={`world-node ${business.active ? '' : 'world-node-offline'} ${active ? 'world-node-active' : ''} ${disrupted ? 'world-node-disrupted' : ''}`} to={`/economy/business/${business.business_id}`} style={{ left: `${left}%`, top: `${top}%` }} aria-label={`Inspect ${business.name}`} onClick={handleClick} initial={{ opacity: 0, scale: reducedMotion ? 1 : 0.82 }} animate={active && !reducedMotion ? { opacity: [0.82, 1, 0.82], scale: [1, 1.08, 1] } : { opacity: business.active ? 1 : 0.55, scale: 1 }} transition={active && !reducedMotion ? { duration: 1.05, ease: 'easeInOut' } : { duration: reducedMotion ? 0 : 0.24 }} whileHover={reducedMotion ? undefined : { scale: 1.04 }}><div className="world-node-ring"><span>{business.name.slice(0, 1)}</span></div><div className="world-node-label"><b>{business.name}</b><small>{business.role} · {Math.round(business.reliability * 100)}% reliable</small></div></MotionLink>;
}

export function WorldPage() {
  const { summary, events, loading, connected, error } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const [selectedBusiness, setSelectedBusiness] = useState<EconomyBusiness | null>(null);
  const mapRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Record<string, HTMLAnchorElement | null>>({});
  const buyerBeamRef = useRef<HTMLAnchorElement | null>(null);
  const counterpartBeamRef = useRef<HTMLAnchorElement | null>(null);
  const businesses = summary?.businesses ?? [];
  const buyer = businesses.find((business) => business.role === 'buyer');
  const contracts = summary?.contracts ?? [];
  const latestEvent = events.at(-1);
  const latestShockIndex = [...events].reverse().findIndex((event) => event.type === 'ShockInjected');
  const latestShock = latestShockIndex >= 0 ? events[events.length - 1 - latestShockIndex] : undefined;
  const shockWindow = latestShock ? events.filter((event) => event.seq >= latestShock.seq) : [];
  const eventIds = new Set([...eventBusinessIds(latestEvent), ...shockWindow.flatMap((event) => [...eventBusinessIds(event)])]);
  const flowActive = Boolean(latestEvent && (flowEvents.has(latestEvent.type) || latestEvent.deal_id));
  const shockActive = shockWindow.some((event) => shockEvents.has(event.type));
  const activeCounterpartId = [...eventBusinessIds(latestEvent)].find((businessId) => businessId !== buyer?.business_id && businesses.some((business) => business.business_id === businessId));

  return <EconomyShell eyebrow="The World / 01" title="A small economy, moving in real time." connected={connected}>
    {error && <div className="economy-error">Backend unavailable — start the mock economy to see live state. <span>{error}</span></div>}
    <section className="economy-hero-grid">
      <div className="economy-hero-copy"><div className="economy-kicker"><span className="pulse-ring" /> Autonomous business network</div><h2>Watch the agents<br /><em><ReactBitsBlurText text="make the call." /></em></h2><p>Businesses discover each other, trade, and keep their books. Every move below is an event from the deterministic economy engine.</p><div className="economy-hero-actions"><Link className="economy-button economy-button-primary" to="/economy/negotiations">Open negotiation room <ArrowUpRight size={15} /></Link><Link className="economy-text-link" to="/economy/scenarios">Break the economy <ArrowUpRight size={14} /></Link></div></div>
      <div className="world-signal-card"><div className="world-signal-top"><span>NETWORK PULSE</span><StatusPill tone="good">{connected ? 'streaming' : 'offline'}</StatusPill></div><div className="world-signal-number">{summary?.clock?.replace('sim-day-', 'D') ?? 'D001'}<span>/ LIVE</span></div><div className="world-signal-chart"><div className="chart-axis"><span>cash flow</span><span>now</span></div><svg viewBox="0 0 420 92" role="img" aria-label="Cash flow signal"><path d="M0 70 C24 68 30 43 58 52 S86 60 110 30 S142 25 166 45 S194 68 216 52 S246 12 274 32 S302 54 330 28 S364 48 420 8" fill="none" stroke="url(#flow)" strokeWidth="2" /><defs><linearGradient id="flow"><stop stopColor="#8cf2c8" /><stop offset="1" stopColor="#f2b35d" /></linearGradient></defs></svg></div><div className="world-signal-footer"><span><i className="signal-dot orange" /> {businesses.length} businesses</span><span><i className="signal-dot green" /> {contracts.length} active deals</span></div></div>
    </section>
    <AnimatedGroup className="economy-stat-grid" preset="blur-slide">
      {[{ label: 'Businesses in orbit', value: businesses.length, icon: Users, note: 'registered agents' }, { label: 'Treasury position', value: buyer?.cash_cents ?? 0, money: true, icon: CircleDollarSign, note: 'Lumen Coffee Co.' }, { label: 'Inventory on hand', value: Object.values(buyer?.inventory ?? {}).reduce((sum, value) => sum + value, 0), icon: Boxes, note: 'units across SKUs' }, { label: 'Policy health', value: `${Math.round((buyer?.reliability ?? 0) * 100)}%`, icon: ShieldCheck, note: 'reserve protected' }].map(({ label, value, icon: Icon, note, money }) => <div className="economy-stat-card" key={label}><div className="stat-card-icon"><Icon size={16} /></div><div className="economy-stat-label">{label}</div><div className="economy-stat-value">{money ? <Money cents={value as number} /> : value}</div><div className="economy-stat-note">{note}</div></div>)}
    </AnimatedGroup>
    <section className="world-lower-grid">
      <div className="economy-panel world-map-panel"><div className="economy-panel-heading"><div><span className="economy-overline">AGENT NETWORK</span><h3>Who is trading with whom</h3></div><span className="economy-panel-meta"><Network size={14} /> {businesses.length} nodes</span></div><div ref={mapRef} className={`world-map ${shockActive ? 'world-map-shock' : ''}`}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{[[20, 49, 48, 23], [20, 49, 74, 47], [20, 49, 37, 77], [20, 49, 77, 78], [20, 49, 58, 66]].map(([x1, y1, x2, y2], index) => <motion.line key={index} x1={x1} y1={y1} x2={x2} y2={y2} className={flowActive ? 'world-flow-line-active' : ''} initial={{ strokeDashoffset: 6 }} animate={flowActive && !reducedMotion ? { strokeDashoffset: [6, 0] } : { strokeDashoffset: flowActive ? 0 : 6 }} transition={flowActive && !reducedMotion ? { duration: 0.9, repeat: 1, ease: 'easeInOut' } : { duration: reducedMotion ? 0 : 0.2 }} />)}</svg>{businesses.map((business, index) => <Node key={business.business_id} business={business} index={index} active={eventIds.has(business.business_id)} disrupted={shockActive && eventIds.has(business.business_id)} reducedMotion={Boolean(reducedMotion)} onSelect={setSelectedBusiness} nodeRef={(node) => { nodeRefs.current[business.business_id] = node; if (business.business_id === buyer?.business_id) buyerBeamRef.current = node; if (business.business_id === activeCounterpartId) counterpartBeamRef.current = node; }} />)}
        {flowActive && buyer && activeCounterpartId && <MagicAnimatedBeam key={`beam-${latestEvent?.seq}`} containerRef={mapRef} fromRef={buyerBeamRef} toRef={counterpartBeamRef} curvature={18} className="world-magic-beam" />}
        <AnimatePresence initial={false}>{selectedBusiness && <motion.aside className="world-inspector" initial={{ opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.98 }} transition={{ duration: reducedMotion ? 0 : 0.26, ease: 'easeOut' }}><button className="world-inspector-close" aria-label="Close business inspector" onClick={() => setSelectedBusiness(null)}><X size={13} /></button><span className="economy-overline">SELECTED BUSINESS</span><strong>{selectedBusiness.name}</strong><small>{selectedBusiness.kind} · {selectedBusiness.role} · {Math.round(selectedBusiness.reliability * 100)}% reliable</small><div className="world-inspector-metrics"><span><b><Money cents={selectedBusiness.cash_cents} /></b> cash</span><span><b>{Object.values(selectedBusiness.inventory).reduce((sum, value) => sum + value, 0)}</b> inventory</span></div><Link className="economy-text-link" to={`/economy/business/${selectedBusiness.business_id}`}>Open full detail <ArrowUpRight size={12} /></Link></motion.aside>}</AnimatePresence>
      </div></div>
      <div className="economy-panel"><div className="economy-panel-heading"><div><span className="economy-overline">EVENT LOG</span><h3>What just happened</h3></div><span className="economy-panel-meta">seq {events.at(-1)?.seq ?? '—'}</span></div>{loading ? <div className="economy-skeleton-list" /> : <EventRail events={events} />}</div>
    </section>
  </EconomyShell>;
}
