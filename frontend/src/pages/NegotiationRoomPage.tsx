/**
 * Agentropolis — Negotiation Room
 *
 * Animated competition environment where supplier offers animate into
 * comparison lanes, counteroffers travel between agent identities, and
 * the negotiation structure is visualized as a timeline rather than a
 * scrolling conversation.
 */

import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect } from 'react';
import {
  ChevronRight,
  Clock3,
  GitCompareArrows,
  MessageSquareText,
  ShieldAlert,
  CheckCircle2,
  Send,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { EconomyShell, EventRail, Money, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import { decideApproval, progressContract } from '@/lib/economy-api';
import { useState } from 'react';
import { AgentAvatar } from '@/components/visual-identity/AgentAvatars';
import { AgentropolisLogo } from '@/components/visual-identity/AgentropolisLogo';
import { motionTokens } from '@/lib/motion';
import { spawnEconomicParticle } from '@/components/ambient/EconomicParticles';

type OfferView = {
  supplier_id: string;
  supplier_name: string;
  score: number;
  offer: {
    proposal_id: string;
    item?: string;
    quantity?: number;
    unit_price_cents?: number;
    delivery_days?: number;
    public_rationale?: string;
  };
  score_breakdown: {
    factors: Record<string, { raw: number; weight: number; contribution: number }>;
    inputs: Record<string, number>;
  };
  reliability_report?: { mode?: string; status?: string };
  round?: number;
  status?: 'offered' | 'countered' | 'accepted' | 'rejected';
};

function formatMoney(cents: number | undefined) {
  const v = cents ?? 0;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v / 100);
}

export function NegotiationRoomPage() {
  const { summary, events, connected, refresh } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [showTimeline, setShowTimeline] = useState(true);
  const [negotiationPhase, setNegotiationPhase] = useState<'idle' | 'offering' | 'countering' | 'agreed' | 'rejected'>('idle');

  const selected = summary?.contracts.find((contract) => contract.contract_id === selectedId) ?? summary?.contracts.at(-1);
  const offers = (summary?.offers ?? []) as OfferView[];
  const sortedOffers = [...offers].sort((a, b) => b.score - a.score);
  const approvals = summary?.approvals.filter((approval) => approval.status === 'pending') ?? [];

  // Determine phase from latest events
  const latestOfferEvent = [...events]
    .reverse()
    .find((e) => ['OfferReceived', 'CounterOfferReceived', 'NegotiationCompleted', 'ContractAccepted'].includes(e.type));

  useEffect(() => {
    if (!latestOfferEvent) return;
    if (latestOfferEvent.type === 'OfferReceived') setNegotiationPhase('offering');
    if (latestOfferEvent.type === 'CounterOfferReceived') setNegotiationPhase('countering');
    if (latestOfferEvent.type === 'NegotiationCompleted' || latestOfferEvent.type === 'ContractAccepted')
      setNegotiationPhase('agreed');
  }, [latestOfferEvent]);

  const handleDecision = async (approvalId: string, approved: boolean) => {
    setBusy(approvalId);
    try {
      await decideApproval(approvalId, approved);
      await refresh();
      setNotice(approved ? 'Approval granted — contract moves to execution.' : 'Approval denied — offer returned to negotiation.');
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Approval failed');
    } finally {
      setBusy(null);
    }
  };

  async function advance(id: string, action: 'ship' | 'deliver' | 'pay') {
    setBusy(id);
    setNotice('');
    try {
      await progressContract(id, action);
      await refresh();
      setNotice(`${action === 'deliver' ? 'Receipt' : action === 'pay' ? 'Payment' : 'Shipment'} recorded by the engine.`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(null);
    }
  }

  return (
    <EconomyShell
      eyebrow="Negotiation room / 02"
      title="Offers, counteroffers, consequences."
      connected={connected}
      actions={
        <span className="economy-header-context">
          <GitCompareArrows size={14} /> {summary?.contracts.length ?? 0} contract threads
        </span>
      }
    >
      {notice && <div className="economy-notice" role="status">{notice}</div>}

      {/* ── Phase indicator ── */}
      <div className="negotiation-phase-banner">
        <motion.div
          className={`phase-indicator phase-${negotiationPhase}`}
          animate={{ opacity: [0.7, 1, 0.7], transition: { duration: 3, repeat: Infinity } }}
        >
          <span className="phase-dot" />
          {negotiationPhase === 'idle' ? 'Awaiting offers' : negotiationPhase === 'offering' ? 'Suppliers offering' : negotiationPhase === 'countering' ? 'Counteroffers in flight' : negotiationPhase === 'agreed' ? 'Agreement reached' : 'Negotiation ended'}
        </motion.div>
      </div>

      {/* ── Supplier comparison panel ── */}
      <section className="economy-panel offers-panel">
        <div className="economy-panel-heading">
          <div>
            <span className="economy-overline">SUPPLIER COMPARISON</span>
            <h3>Animated offer lanes</h3>
          </div>
          <span className="economy-panel-meta">price · delivery · reliability · owner preference</span>
        </div>

        <motion.div
          className="offer-card-grid"
          layout
          initial={reducedMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reducedMotion ? 0 : 0.4 }}
        >
          <AnimatePresence initial={false} mode="popLayout">
            {sortedOffers.slice(0, 6).map((item) => {
              const isSelected = selected?.contract_id === item.offer.proposal_id;
              const rank = sortedOffers.indexOf(item) + 1;
              return (
                <motion.article
                  className={`offer-card ${isSelected ? 'selected' : ''} offer-rank-${rank}`}
                  layout
                  key={item.offer.proposal_id}
                  initial={reducedMotion ? false : { opacity: 0, y: 20, scale: 0.95 }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    transition: { duration: reducedMotion ? 0 : 0.3, delay: rank * 0.08, ease: 'backOut' },
                  }}
                  exit={reducedMotion ? undefined : { opacity: 0, scale: 0.9, y: 10 }}
                  onClick={() => setSelectedId(item.offer.proposal_id)}
                >
                  <div className="offer-card-header">
                    <span className="offer-rank">0{rank}</span>
                    <AgentAvatar
                      role="supplier"
                      status={item.status === 'accepted' ? 'completed' : item.status === 'rejected' ? 'error' : 'active'}
                      size={28}
                    />
                    <div className="offer-supplier-info">
                      <b>{item.supplier_name || item.supplier_id}</b>
                      <StatusPill tone={item.score >= 65 ? 'good' : 'warn'}>{item.score.toFixed(1)} / 100</StatusPill>
                    </div>
                    <StatusPill tone={item.status === 'accepted' ? 'good' : item.status === 'rejected' ? 'bad' : 'neutral'}>{item.status ?? 'offered'}</StatusPill>
                  </div>

                  <div className="offer-card-metrics">
                    <span>
                      <small>UNIT PRICE</small>
                      <strong><Money cents={item.offer.unit_price_cents ?? 0} /></strong>
                    </span>
                    <span>
                      <small>DELIVERY</small>
                      <strong><Clock3 size={12} /> {item.offer.delivery_days ?? 0}d</strong>
                    </span>
                    <span>
                      <small>RELIABILITY</small>
                      <strong>{Math.round((item.score_breakdown.inputs.reliability ?? 0) * 100)}%</strong>
                    </span>
                  </div>

                  <div className="offer-score-breakdown">
                    {Object.entries(item.score_breakdown.factors).map(([factor, value]) => (
                      <span key={factor}>
                        <motion.div
                          className="factor-bar"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.round(value.raw * 100)}%` }}
                          transition={{ duration: reducedMotion ? 0 : 0.6, delay: 0.2 }}
                        />
                        <label>{factor.replace('_', ' ')} {Math.round(value.contribution * 100)}%</label>
                      </span>
                    ))}
                  </div>

                  <p>{item.offer.public_rationale ?? 'Typed supplier offer scored by the deterministic policy.'}</p>

                  {isSelected && (
                    <div className="offer-selected-badge">
                      <CheckCircle2 size={14} /> Selected for contract
                    </div>
                  )}
                </motion.article>
              );
            })}
          </AnimatePresence>
          {!offers.length && <div className="economy-empty compact">No live offers yet; start the simulation or trigger the scheduler.</div>}
        </motion.div>
      </section>

      {/* ── Negotiation structure ── */}
      <section className="negotiation-layout">
        {/* Live threads list */}
        <div className="economy-panel negotiation-list-panel">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">LIVE THREADS</span>
              <h3>Active negotiations</h3>
            </div>
            <span className="economy-panel-meta">{summary?.contracts.length ?? 0} total</span>
          </div>
          <AnimatePresence initial={false}>
            {(summary?.contracts ?? []).map((contract) => (
              <motion.button
                layout
                className={`negotiation-list-item ${selected?.contract_id === contract.contract_id ? 'selected' : ''}`}
                initial={reducedMotion ? false : { opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reducedMotion ? undefined : { opacity: 0, x: -8 }}
                transition={{ duration: reducedMotion ? 0 : 0.2 }}
                key={contract.contract_id}
                onClick={() => setSelectedId(contract.contract_id)}
              >
                <div className="negotiation-avatar">
                  {contract.item.slice(0, 1).toUpperCase()}
                </div>
                <div className="negotiation-list-copy">
                  <b>{contract.item.replaceAll('_', ' ')}</b>
                  <span>{contract.supplier_id} → {contract.buyer_id}</span>
                  <small><Clock3 size={12} /> {contract.delivery_days} day delivery</small>
                </div>
                <div className="negotiation-list-price">
                  <Money cents={contract.total_cents} />
                  <StatusPill tone={contract.status === 'paid' ? 'good' : 'warn'}>{contract.status}</StatusPill>
                </div>
                <ChevronRight size={15} />
              </motion.button>
            ))}
            {!summary?.contracts.length && <div className="economy-empty">No negotiation threads yet.</div>}
          </AnimatePresence>
        </div>

        {/* Detail column */}
        <div className="negotiation-detail-column">
          <div className="economy-panel offer-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">WHY THIS OFFER</span>
                <h3>{selected?.item.replaceAll('_', ' ') ?? 'Waiting for a proposal'}</h3>
              </div>
              {selected && <StatusPill tone={selected.status === 'defaulted' ? 'bad' : 'good'}>{selected.status}</StatusPill>}
            </div>
            {selected ? (
              <>
                <div className="offer-metrics">
                  <div>
                    <span>UNIT PRICE</span>
                    <strong><Money cents={selected.unit_price_cents} /></strong>
                  </div>
                  <div>
                    <span>QUANTITY</span>
                    <strong>{selected.quantity} {selected.unit ?? 'unit'}</strong>
                  </div>
                  <div>
                    <span>RELIABILITY</span>
                    <strong>{Math.round(selected.reliability * 100)}%</strong>
                  </div>
                  <div>
                    <span>DELIVERY</span>
                    <strong>{selected.delivery_days} days</strong>
                  </div>
                </div>
                <div className="why-card">
                  <div className="why-card-icon"><MessageSquareText size={16} /></div>
                  <div>
                    <span className="economy-overline">PUBLIC RATIONALE</span>
                    <p>{selected.rationale}</p>
                    <small>Public decision summary from the economy engine.</small>
                  </div>
                </div>
                <div className="contract-state-grid">
                  <div>
                    <span>FULFILLMENT</span>
                    <b>{(selected.fulfillment_state ?? selected.state ?? selected.status).replaceAll('_', ' ')}</b>
                  </div>
                  <div>
                    <span>PAYMENT</span>
                    <b>{(selected.payment_state ?? 'not submitted').replaceAll('_', ' ')}</b>
                  </div>
                  <div>
                    <span>RECEIVED</span>
                    <b>{selected.received_quantity ?? 0} / {selected.quantity}</b>
                  </div>
                </div>
                <div className="contract-actions">
                  {(selected.fulfillment_state?.toLowerCase() === 'reserved' || selected.fulfillment_state?.toLowerCase() === 'accepted') && (
                    <button className="economy-button economy-button-small economy-button-secondary" disabled={busy === selected.contract_id} onClick={() => void advance(selected.contract_id, 'ship')}>
                      Record shipment
                    </button>
                  )}
                  {selected.fulfillment_state?.toLowerCase() === 'shipped' && (
                    <button className="economy-button economy-button-small economy-button-primary" disabled={busy === selected.contract_id} onClick={() => void advance(selected.contract_id, 'deliver')}>
                      Confirm receipt
                    </button>
                  )}
                  {selected.payment_state === 'SUBMITTED' && (
                    <button className="economy-button economy-button-small economy-button-primary" disabled={busy === selected.contract_id} onClick={() => void advance(selected.contract_id, 'pay')}>
                      Authorize payment
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="economy-empty compact">Select a negotiation thread to inspect the offer structure.</div>
            )}
          </div>

          {/* Approval panel */}
          <div className="economy-panel approval-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">HUMAN GATE</span>
                <h3>Approval queue</h3>
              </div>
              <StatusPill tone={approvals.length ? 'warn' : 'good'}>{approvals.length ? `${approvals.length} needs you` : 'clear'}</StatusPill>
            </div>
            <AnimatePresence initial={false} mode="popLayout">
              {approvals.map((approval) => (
                <motion.div
                  className="approval-row"
                  layout
                  key={approval.approval_id}
                  initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reducedMotion ? undefined : { opacity: 0, height: 0, paddingBlock: 0 }}
                  transition={{ duration: reducedMotion ? 0 : 0.22 }}
                >
                  <div className="approval-icon"><ShieldAlert size={16} /></div>
                  <div className="approval-copy">
                    <b>Approve {approval.proposal_id}</b>
                    <span>{approval.reason}</span>
                  </div>
                  <div className="approval-amount"><Money cents={approval.amount_cents} /></div>
                  <button className="economy-button economy-button-small economy-button-primary" disabled={busy === approval.approval_id} onClick={() => void handleDecision(approval.approval_id, true)}>
                    Approve
                  </button>
                  <button className="economy-icon-button" disabled={busy === approval.approval_id} onClick={() => void handleDecision(approval.approval_id, false)} aria-label="Deny approval">
                    ×
                  </button>
                </motion.div>
              ))}
              {!approvals.length && <div className="economy-empty compact">All high-risk actions are resolved.</div>}
            </AnimatePresence>
          </div>
        </div>

        {/* Decision trace */}
        <div className="economy-panel negotiation-events">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">DECISION TRACE</span>
              <h3>Agent activity</h3>
            </div>
          </div>
          <EventRail
            events={events.filter((e) =>
              ['OfferReceived', 'CounterOfferReceived', 'NegotiationCompleted', 'ContractAccepted', 'PaymentConfirmed', 'InvoiceMatched', 'ApprovalRequested', 'RecoveryPlanProposed'].includes(e.type)
            )}
            limit={11}
          />
        </div>
      </section>
    </EconomyShell>
  );
}

