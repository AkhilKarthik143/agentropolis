/**
 * Agentropolis — Procurement Marketplace
 *
 * Interactive agentic shopping experience. Supplier cards emerge dynamically
 * as suppliers respond, offer comparisons animate, and price/delivery
 * tradeoffs are visualized as moving elements.
 */

import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Clock3, Link2, ShieldCheck, Truck, Factory, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EconomyShell, Money, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import type { EconomyOffer } from '@/types/economy';
import { AgentAvatar } from '@/components/visual-identity/AgentAvatars';
import { AgentropolisLogo } from '@/components/visual-identity/AgentropolisLogo';

function supplierName(item: EconomyOffer, businesses: { business_id: string; name: string }[]) {
  return businesses.find((business) => business.business_id === item.supplier_id)?.name ?? item.supplier_id;
}

export function ProcurementPage() {
  const { summary, connected, loading, error } = useEconomyEvents();
  const reducedMotion = useReducedMotion();
  const offers = [...(summary?.offers ?? [])].sort((a, b) => b.score - a.score);
  const selected = offers[0];
  const quantity = selected?.offer.quantity ?? 0;
  const totalCents = (selected?.offer.unit_price_cents ?? 0) * quantity;
  const buyer = summary?.businesses.find((business) => business.role === 'buyer');
  const overLimit = totalCents > (buyer?.spend_limit_cents ?? 0);

  const [discovered, setDiscovered] = useState<number>(0);

  // Animate discovery count up
  useEffect(() => {
    if (reducedMotion) {
      setDiscovered(offers.length);
      return;
    }
    let t: number | null = null;
    let current = discovered;
    const target = offers.length;
    const step = () => {
      if (current < target) {
        current = Math.min(current + 1, target);
        setDiscovered(current);
        t = window.setTimeout(step, 60);
      }
    };
    t = window.setTimeout(step, 60);
    return () => { if (t) clearTimeout(t); };
  }, [offers.length, discovered, reducedMotion]);

  return (
    <EconomyShell
      eyebrow="Procurement / 06"
      title="Source with intent."
      connected={connected}
      actions={
        <Link className="economy-button economy-button-small economy-button-primary" to="/economy/negotiations">
          <Users size={13} /> Open negotiation room
        </Link>
      }
    >
      {error && (
        <div className="economy-error">
          Live procurement data unavailable. <span>{error}</span>
        </div>
      )}

      <section className="procurement-intro">
        <div>
          <div className="economy-kicker">
            <span className="pulse-ring" /> Agentic procurement · simulated commerce
          </div>
          <p>
            Compare suppliers by reliability-adjusted cost, delivery risk, and policy fit. Every offer below
            comes from the economy engine as agents negotiate on your behalf.
          </p>
        </div>
        <div className="procurement-limit">
          <span>SPENDING LIMIT</span>
          <b><Money cents={buyer?.spend_limit_cents ?? 0} /></b>
        </div>
      </section>

      <section className="procurement-layout">
        <div className="economy-panel procurement-results">
          <div className="economy-panel-heading">
            <div>
              <span className="economy-overline">ENGINE-SCORED OFFERS</span>
              <h3>{selected?.offer.item?.replaceAll('_', ' ') ?? 'Supplier matches'}</h3>
            </div>
            <span className="economy-panel-meta">{discovered} of {offers.length} suppliers responded</span>
          </div>

          {loading && <div className="economy-skeleton-list" />}
          {!loading && offers.length === 0 && (
            <div className="economy-empty">
              <AgentropolisLogo size={40} className="empty-logo" />
              <p>No supplier offers are available yet. Start the economy scheduler or open a negotiation to populate this workspace.</p>
            </div>
          )}

          <div className="procurement-results-list">
            <AnimatePresence initial={false} mode="popLayout">
              {offers.map((item, index) => {
                const name = supplierName(item, summary?.businesses ?? []);
                const offer = item.offer;
                const isSelected = index === 0;
                const isDiscovered = index < discovered;
                return (
                  <motion.article
                    className={`procurement-result ${isSelected ? 'selected' : ''} ${!isDiscovered ? 'pending-discovery' : ''}`}
                    layout
                    key={offer.proposal_id}
                    initial={reducedMotion ? false : { opacity: 0, y: 12, scale: 0.96 }}
                    animate={{
                      opacity: 1,
                      y: 0,
                      scale: 1,
                      transition: { duration: reducedMotion ? 0 : 0.3, delay: index * 0.06, ease: 'backOut' },
                    }}
                    exit={{ opacity: 0, scale: 0.94, y: 10 }}
                  >
                    <div className="procurement-result-rank">{isDiscovered ? `0${index + 1}` : '—'}</div>
                    <div className="procurement-result-copy">
                      <b>{name}</b>
                      <span>{offer.public_rationale ?? 'Typed supplier offer scored by the economy policy.'}</span>
                      <small>
                        <ShieldCheck size={12} />
                        {Math.round(item.score)} match · {item.reliability_report?.status ?? 'not reported'}
                      </small>
                    </div>
                    <div className="procurement-result-metric">
                      <span>UNIT PRICE</span>
                      <strong><Money cents={offer.unit_price_cents ?? 0} /></strong>
                    </div>
                    <div className="procurement-result-metric">
                      <span>DELIVERY</span>
                      <strong><Clock3 size={12} /> {offer.delivery_days ?? 0}d</strong>
                    </div>
                    <div className="procurement-result-metric">
                      <span>AGENT</span>
                      <AgentAvatar role="supplier" status="active" size={18} />
                    </div>
                    <StatusPill tone={isSelected ? 'good' : 'neutral'}>
                      {isSelected ? 'recommended' : 'compare'}
                    </StatusPill>
                  </motion.article>
                );
              })}
            </AnimatePresence>
          </div>

          {selected && (
            <div className="procurement-reason">
              <div>
                <span className="economy-overline">
                  WHY THE AGENT CHOSE {supplierName(selected, summary?.businesses ?? []).toUpperCase()}
                </span>
                <p>{selected.offer.public_rationale ?? 'The engine selected the highest-scoring supplier based on the current policy.'}</p>
              </div>
              <Link to="/economy/negotiations">
                <Link2 size={13} /> Inspect reasoning
              </Link>
            </div>
          )}
        </div>

        <aside className="economy-panel procurement-summary">
          <div className="economy-overline">PURCHASE SUMMARY</div>
          <h3>{selected ? supplierName(selected, summary?.businesses ?? []) : 'Waiting for a match'}</h3>
          {selected ? (
            <>
              <div className="procurement-total">
                <span>Estimated total</span>
                <strong><MotionAnimatedNumber value={totalCents / 100} prefix="$" decimals={2} /></strong>
              </div>
              <div className="procurement-summary-row">
                <span>Quantity</span>
                <b>{quantity || '—'} units</b>
              </div>
              <div className="procurement-summary-row">
                <span>Delivery</span>
                <b>{selected.offer.delivery_days ?? '—'} days</b>
              </div>
              <div className="procurement-summary-row">
                <span>Trust signal</span>
                <b className="money-positive">{Math.round(selected.score)} / 100</b>
              </div>
              <div className={`procurement-alert ${overLimit ? 'warn' : 'good'}`}>
                <span />
                {overLimit
                  ? 'Human approval required: request exceeds the business spend limit.'
                  : 'Within policy: eligible for agent execution.'}
              </div>
              <Link to="/economy/negotiations" className="economy-button economy-button-primary procurement-cta">
                {overLimit ? 'Review approval queue' : 'Inspect contract and fulfillment'}
              </Link>
              <div className="procurement-disclaimer">Simulated purchase rail. No Visa network authorization or real funds.</div>
            </>
          ) : (
            <div className="economy-empty compact">
              <Factory size={28} className="empty-icon" />
              <p>No purchase can be prepared until the backend returns a supplier offer.</p>
            </div>
          )}
        </aside>
      </section>
    </EconomyShell>
  );
}

function MotionAnimatedNumber({ value, prefix = '', decimals = 0 }: { value: number; prefix?: string; decimals?: number }) {
  return (
    <motion.span
      animate={{ scale: [1, 1.15, 1] }}
      transition={{ duration: 0.6, repeat: Infinity, ease: 'easeInOut' }}
    >
      {prefix}{new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)}
    </motion.span>
  );
}

