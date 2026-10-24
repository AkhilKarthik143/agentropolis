/**
 * Agentropolis — Financial Control Tower
 *
 * Precise, confident, sophisticated fintech motion. Money movements are
 * visualized with distinct animations for each payment status:
 * proposed → awaiting approval → processing → confirmed → failed → reconciled.
 *
 * A payment in processing must never visually appear settled.
 */

import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BookOpenCheck,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  WalletCards,
  ArrowRight,
  PauseCircle,
  PlayCircle,
} from 'lucide-react';
import { AnimatedNumber } from '@/components/motion/AnimatedNumber';
import { EconomyShell, EventRail, Money, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import { decideApproval, reconcilePayment } from '@/lib/economy-api';
import { AgentAvatar } from '@/components/visual-identity/AgentAvatars';
import { AgentropolisLogo } from '@/components/visual-identity/AgentropolisLogo';
import { spawnEconomicParticle } from '@/components/ambient/EconomicParticles';
import type { EconomySummary } from '@/types/economy';

interface PaymentView {
  payment_id: string;
  obligation_id: string;
  payer: string;
  payee: string;
  amount_cents: number;
  currency: string;
  rail: string;
  status: string;
  attempts: number;
  idempotency_key: string;
  authorization_hash: string;
  provider_transaction_id?: string;
  reconciliation_status: string;
  error?: string;
}

export function ControlTowerPage() {
  const { summary, events, connected, refresh, error } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const [businessId, setBusinessId] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [highlightPayment, setHighlightPayment] = useState<string | null>(null);

  const buyer = summary?.businesses.find((b) => b.business_id === businessId) ?? summary?.businesses.find((b) => b.role === 'buyer');
  const entries = summary?.ledger.filter((e) => e.business_id === buyer?.business_id).slice(-8).reverse() ?? [];
  const cash = buyer?.cash_cents ?? 0;
  const reserve = buyer?.reserve_cents ?? 0;
  const finance = summary?.finance;
  const reconciliation = Array.isArray(summary?.reconciliation) ? summary.reconciliation : [];
  const matched = reconciliation.length > 0 && reconciliation.every((r) => r.ok === true);
  const payments = (summary?.payments ?? []) as PaymentView[];
  const filteredPayments = payments.filter((p) => p.payer === buyer?.business_id || p.payee === buyer?.business_id);
  const approvals = (summary?.approvals ?? []).filter((a) => a.status === 'pending');
  const blocked = events.filter((e) => ['ACTION_BLOCKED', 'PaymentFailed', 'ReconciliationConflict', 'PAYMENT_FAILED'].includes(e.type)).slice(-4).reverse();

  async function reconcile(id: string) {
    setBusy(id);
    setNotice('');
    setHighlightPayment(id);
    try {
      await reconcilePayment(id);
      await refresh();
      setNotice('Provider transaction reconciled against the payment obligation.');
      setTimeout(() => setHighlightPayment(null), 1500);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Reconciliation failed');
      setBusy(null);
    }
  }

  async function approve(id: string, approved: boolean) {
    setBusy(id);
    try {
      await decideApproval(id, approved);
      await refresh();
      setNotice(approved ? 'Approval granted.' : 'Approval denied.');
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Approval failed');
    } finally {
      setBusy(null);
    }
  }

  const cashSpring = {
    stiffness: 260,
    damping: 28,
    mass: 0.8,
  };

  return (
    <EconomyShell
      eyebrow="Financial control tower / 03"
      title="Money moves. The books remember."
      connected={connected}
      actions={
        <>
          <AgentropolisLogo size={24} style={{ verticalAlign: 'middle', marginRight: 10 }} />
          <button type="button" className="economy-icon-button" aria-label="Refresh economy data" onClick={() => void refresh()}>
            <RefreshCw size={15} />
          </button>
        </>
      }
    >
      {(notice || error) && (
        <div className="economy-notice" role="status">{notice || error}</div>
      )}

      {/* ── Hero: Treasury balance with smooth transitions ── */}
      <section className="control-hero">
        <div>
          <label className="treasury-selector">
            <span className="economy-overline">BUSINESS TREASURY</span>
            <select aria-label="Treasury business" value={buyer?.business_id ?? ''} onChange={(e) => setBusinessId(e.target.value)}>
              {summary?.businesses.map((b) => (
                <option key={b.business_id} value={b.business_id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <div className="control-cash-wrapper">
            <AnimatedNumber value={cash / 100} prefix="$" decimals={2} springOptions={cashSpring} />
          </div>
          <p>
            Cash balance · reserve{' '}
            <MotionMoney cents={reserve} />
          </p>
          <div className={`control-reserve-indicator ${cash < reserve ? 'below' : 'met'}`}>
            <span>{cash >= reserve ? 'Cash meets the policy floor.' : 'Cash is below the policy floor.'}</span>
          </div>
        </div>
        <div className="control-health">
          <div className={`health-ring ${cash < reserve ? 'at-risk' : ''}`}>
            <span>{reserve ? Math.round((cash / reserve) * 100) : '—'}%</span>
          </div>
          <div>
            <b>Reserve coverage</b>
            <span>{cash >= reserve ? 'Cash meets the policy floor.' : 'Cash is below the policy floor.'}</span>
          </div>
        </div>
      </section>

      {/* ── Key metrics ── */}
      <section className="economy-stat-grid control-stat-grid">
        {[
          { label: 'Spendable liquidity', value: Math.max(0, cash - reserve), money: true, icon: WalletCards, note: 'cash less protected reserve' },
          { label: 'Pending approvals', value: approvals.length, icon: AlertTriangle, note: 'requires operator review' },
          { label: 'Journal entries', value: summary?.ledger.length ?? 0, icon: BookOpenCheck, note: 'internal double-entry ledger' },
          { label: 'Reconciliation', value: reconciliation.length ? (matched ? 'MATCHED' : 'MISMATCH') : 'PENDING', icon: CheckCircle2, note: 'simulated bank vs ledger cash' },
        ].map(({ label, value, money, icon: Icon, note }) => (
          <div className="economy-stat-card" key={label}>
            <div className="stat-card-icon"><Icon size={16} /></div>
            <div className="economy-stat-label">{label}</div>
            <div className="economy-stat-value">{money ? <Money cents={Number(value)} /> : value}</div>
            <div className="economy-stat-note">{note}</div>
          </div>
        ))}
      </section>

      {/* ── Payment operations ── */}
      <section className="tower-grid">
        <div className="economy-panel">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">PAYMENT OPERATIONS</span>
              <h3>Obligation → provider → reconciliation</h3>
            </div>
            <StatusPill tone="neutral">{summary?.mode ?? 'not connected'}</StatusPill>
          </div>
          <div className="payment-list">
            <AnimatePresence initial={false} mode="popLayout">
              {filteredPayments.slice(-8).reverse().map((p) => {
                const isProcessing = p.status === 'SUBMITTED' || p.status === 'UNCERTAIN';
                const isConfirmed = ['CONFIRMED', 'RECONCILED'].includes(p.status);
                const isFailed = ['FAILED', 'CANCELLED', 'REVERSED'].includes(p.status);
                const statusTone = isConfirmed ? 'good' : isFailed ? 'bad' : 'warn';
                return (
                  <motion.div
                    className={`payment-record ${isProcessing ? 'payment-processing' : ''} ${isConfirmed ? 'payment-confirmed' : ''} ${isFailed ? 'payment-failed' : ''} ${highlightPayment === p.payment_id ? 'payment-highlight' : ''}`}
                    key={String(p.payment_id)}
                    initial={reducedMotion ? false : { opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10, transition: { duration: reducedMotion ? 0 : 0.2 } }}
                  >
                    <div className="payment-record-top">
                      <div>
                        <b>{String(p.payer)} → {String(p.payee)}</b>
                        <small>{String(p.payment_id)}</small>
                      </div>
                      <strong className={isConfirmed ? 'money-confirmed' : isFailed ? 'money-failed' : ''}>
                        <Money cents={Number(p.amount_cents)} />
                      </strong>
                    </div>
                    <div className="payment-record-bottom">
                      <StatusPill tone={statusTone}>{String(p.status)}</StatusPill>
                      <span>{String(p.rail)} rail · {Number(p.attempts)} attempts</span>
                      {p.status === 'CONFIRMED' && (
                        <button
                          className="economy-button economy-button-small economy-button-secondary"
                          disabled={busy === p.payment_id}
                          onClick={() => void reconcile(String(p.payment_id))}
                        >
                          Reconcile
                        </button>
                      )}
                    </div>
                    {Boolean(p.provider_transaction_id) && (
                      <small className="payment-provider">Provider reference · {String(p.provider_transaction_id)}</small>
                    )}
                    {Boolean(p.error) && <p className="payment-error">{String(p.error)}</p>}
                  </motion.div>
                );
              })}
            </AnimatePresence>
            {!payments.length && <div className="economy-empty compact">No payment obligations for this business.</div>}
            <p className="finance-disclosure">
              These are simulated banking operations. An approved obligation does not imply funds moved.{' '}
              <span style={{ fontStyle: 'italic' }}>Processing state means the payment is in flight — not yet settled.</span>
            </p>
          </div>
        </div>

        <div className="economy-panel">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">HUMAN GATE</span>
                <h3>Protected operations</h3>
              </div>
              <StatusPill tone={approvals.length ? 'warn' : 'good'}>{approvals.length} pending</StatusPill>
            </div>
            <AnimatePresence initial={false} mode="popLayout">
              {approvals.map((a) => (
                <motion.div className="payment-record approval-record" key={a.approval_id}>
                  <div className="payment-record-top">
                    <div>
                      <b>{a.proposal_id}</b>
                      <small>{a.reason}</small>
                    </div>
                    <strong><Money cents={a.amount_cents} /></strong>
                  </div>
                  <div className="payment-record-bottom">
                    <StatusPill tone="warn">Awaiting approval</StatusPill>
                    <span>Human operator decision required</span>
                    <button className="economy-button economy-button-small economy-button-primary" disabled={busy === a.approval_id} onClick={() => void approve(a.approval_id, true)}>
                      Approve
                    </button>
                    <button className="economy-icon-button" disabled={busy === a.approval_id} onClick={() => void approve(a.approval_id, false)} aria-label="Deny approval">
                      ×
                    </button>
                  </div>
                </motion.div>
              ))}
              {!approvals.length && <div className="economy-empty compact">No operations awaiting your approval.</div>}
            </AnimatePresence>
          </div>
        </section>

        {/* ── Ledger + reconciliation ── */}
        <section className="tower-grid">
          <div className="economy-panel ledger-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">INTERNAL DOUBLE-ENTRY LEDGER</span>
                <h3>Latest postings</h3>
              </div>
              <span className="economy-panel-meta"><CreditCard size={14} /> integer cents</span>
            </div>
            <div className="ledger-table">
              <div className="ledger-row ledger-head">
                <span>POSTING</span>
                <span>DEBIT</span>
                <span>CREDIT</span>
                <span>PROOF</span>
              </div>
              <AnimatePresence initial={false} mode="popLayout">
                {entries.map((entry) => {
                  const debit = entry.lines.reduce((s, l) => s + Math.max(0, l.amount_cents), 0);
                  const credit = entry.lines.reduce((s, l) => s + Math.min(0, l.amount_cents), 0);
                  const balanced = debit + credit === 0;
                  return (
                    <motion.div
                      className="ledger-row"
                      layout
                      key={entry.entry_id}
                      initial={reducedMotion ? false : { opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: reducedMotion ? 0 : 0.22 }}
                    >
                      <div>
                        <b>{entry.memo}</b>
                        <small>{entry.entry_id}</small>
                      </div>
                      <span className="ledger-amount">
                        <ArrowUpRight size={13} />
                        <Money cents={debit} />
                      </span>
                      <span className="ledger-amount negative">
                        <ArrowDownRight size={13} />
                        <Money cents={-credit} />
                      </span>
                      <StatusPill tone={balanced ? 'good' : 'bad'}>{balanced ? 'balanced' : 'mismatch'}</StatusPill>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </div>

          <div className="economy-panel balances-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">NETWORK ACCOUNTS</span>
                <h3>Bank ↔ ledger cash</h3>
              </div>
            </div>
            {reconciliation.map((r) => (
              <div className="reconciliation-row" key={String(r.business_id)}>
                <div>
                  <b>{summary?.businesses.find((b) => b.business_id === r.business_id)?.name ?? String(r.business_id)}</b>
                  <small>
                    Bank <Money cents={Number(r.bank_cash_cents)} /> · Ledger <Money cents={Number(r.ledger_cash_cents)} />
                  </small>
                </div>
                <StatusPill tone={r.ok ? 'good' : 'bad'}>{r.ok ? 'matched' : 'mismatch'}</StatusPill>
              </div>
            ))}
          </div>
        </section>

        {/* ── Purchase controls + chart of accounts ── */}
        <section className="tower-grid">
          <div className="economy-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">PURCHASE CONTROLS</span>
                <h3>PO → receipt → invoice → match</h3>
              </div>
            </div>
            {(finance?.purchase_orders ?? []).slice(-5).reverse().map((po) => {
              const invoice = finance?.invoices.find((i) => i.po_id === po.po_id);
              const match = finance?.matches.find((m) => m.po_id === po.po_id);
              return (
                <div className="payment-record" key={po.po_id}>
                  <div className="payment-record-top">
                    <div>
                      <b>{po.item.replaceAll('_', ' ')} · {po.quantity} units</b>
                      <small>{po.po_id} · {invoice?.invoice_number ?? 'receipt / invoice pending'}</small>
                    </div>
                    <Money cents={invoice?.amount_cents ?? po.total_cents} />
                  </div>
                  <StatusPill tone={match?.status === 'matched' ? 'good' : 'warn'}>
                    {match?.status ?? 'unmatched'}
                  </StatusPill>
                  {invoice && (
                    <p className="finance-disclosure">
                      Due {invoice.due_date} · {invoice.payment_terms} · {invoice.cost_center}
                    </p>
                  )}
                </div>
              );
            })}
            {!finance?.purchase_orders.length && <div className="economy-empty compact">No purchase orders yet.</div>}
          </div>

          <div className="economy-panel balances-panel">
            <div className="economy-panel-heading">
              <div>
                <span className="economy-overline">CHART OF ACCOUNTS</span>
                <h3>Network trial balance</h3>
              </div>
              <StatusPill tone={summary?.ledger_proof?.balanced ? 'good' : 'warn'}>
                {summary?.ledger_proof?.balanced ? 'balanced' : 'unverified'}
              </StatusPill>
            </div>
            <div className="balance-list">
              {Object.entries(summary?.trial_balance ?? {})
                .filter(([, amount]) => amount !== 0)
                .map(([account, amount]) => (
                  <div className="balance-row" key={account}>
                    <span>{account}</span>
                    <strong><Money cents={amount} /></strong>
                  </div>
                ))}
            </div>
          </div>
        </section>

        {/* ── Event trail ── */}
        <section className="economy-panel">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">SIMULATION EVENT TRAIL</span>
              <h3>Every action has a receipt</h3>
            </div>
          </div>
          <EventRail events={events} limit={8} />
        </section>
    </EconomyShell>
  );
}

/** Money component with local status styling (avoids circular import issues) */
function MotionMoney({ cents }: { cents: number }) {
  const prefix = cents < 0 ? '-' : '';
  return (
    <span className={cents < 0 ? 'money-negative' : ''}>
      {prefix}${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Math.abs(cents / 100))}
    </span>
  );
}