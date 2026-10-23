import { Clock3, Link2, ShoppingCart, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EconomyShell, Money, StatusPill } from '@/components/economy/EconomyShell';
import { useEconomyEvents } from '@/hooks/useEconomyEvents';
import type { EconomyOffer } from '@/types/economy';

function supplierName(item: EconomyOffer, businesses: { business_id: string; name: string }[]) {
  return businesses.find((business) => business.business_id === item.supplier_id)?.name ?? item.supplier_id;
}

export function ProcurementPage() {
  const { summary, connected, loading, error } = useEconomyEvents();
  const offers = [...(summary?.offers ?? [])].sort((a, b) => b.score - a.score);
  const selected = offers[0];
  const quantity = selected?.offer.quantity ?? 0;
  const totalCents = (selected?.offer.unit_price_cents ?? 0) * quantity;
  const overLimit = totalCents > (summary?.businesses.find((business) => business.role === 'buyer')?.spend_limit_cents ?? 0);

  return (
    <EconomyShell
      eyebrow="Procurement / 06"
      title="Source with intent."
      connected={connected}
      actions={<Link className="economy-button economy-button-small economy-button-primary" to="/economy/negotiations"><ShoppingCart size={13} /> Open negotiation room</Link>}
    >
      {error && <div className="economy-error">Live procurement data unavailable. <span>{error}</span></div>}
      <section className="procurement-intro">
        <div>
          <div className="economy-kicker"><span className="pulse-ring" /> Visa agentic shopping</div>
          <p>Compare suppliers by reliability-adjusted cost, delivery risk, and policy fit. Every offer below comes from the economy engine.</p>
        </div>
        <div className="procurement-limit"><span>SPENDING LIMIT</span><b><Money cents={summary?.businesses.find((business) => business.role === 'buyer')?.spend_limit_cents ?? 0} /></b></div>
      </section>

      <section className="procurement-layout">
        <div className="economy-panel procurement-results">
          <div className="economy-panel-heading">
            <div><span className="economy-overline">LIVE REQUEST · PR-2284</span><h3>Precision housings · supplier matches</h3></div>
            <span className="economy-panel-meta">{offers.length} ranked</span>
          </div>
          {loading && <div className="economy-skeleton-list" />}
          {!loading && offers.length === 0 && <div className="economy-empty">No supplier offers are available yet. Start the economy scheduler or open a negotiation to populate this workspace.</div>}
          <div className="procurement-results-list">
            {offers.map((item, index) => {
              const name = supplierName(item, summary?.businesses ?? []);
              const offer = item.offer;
              return <article className={`procurement-result ${index === 0 ? 'selected' : ''}`} key={offer.proposal_id}>
                <div className="procurement-result-rank">0{index + 1}</div>
                <div className="procurement-result-copy"><b>{name}</b><span>{offer.public_rationale ?? 'Typed supplier offer scored by the economy policy.'}</span><small><ShieldCheck size={12} /> {Math.round(item.score)} match · {item.reliability_report?.status ?? 'verified'}</small></div>
                <div className="procurement-result-metric"><span>UNIT PRICE</span><strong><Money cents={offer.unit_price_cents ?? 0} /></strong></div>
                <div className="procurement-result-metric"><span>DELIVERY</span><strong><Clock3 size={12} /> {offer.delivery_days ?? 0}d</strong></div>
                <StatusPill tone={index === 0 ? 'good' : 'neutral'}>{index === 0 ? 'recommended' : 'compare'}</StatusPill>
              </article>;
            })}
          </div>
          {selected && <div className="procurement-reason"><div><span className="economy-overline">WHY THE AGENT CHOSE {supplierName(selected, summary?.businesses ?? []).toUpperCase()}</span><p>{selected.offer.public_rationale ?? 'The engine selected the highest-scoring supplier based on the current policy.'}</p></div><Link to="/economy/negotiations"><Link2 size={13} /> Inspect reasoning</Link></div>}
        </div>

        <aside className="economy-panel procurement-summary">
          <div className="economy-overline">PURCHASE SUMMARY</div>
          <h3>{selected ? supplierName(selected, summary?.businesses ?? []) : 'Waiting for a match'}</h3>
          {selected ? <>
            <div className="procurement-total"><span>Estimated total</span><strong><Money cents={totalCents} /></strong></div>
            <div className="procurement-summary-row"><span>Quantity</span><b>{quantity || '—'} units</b></div>
            <div className="procurement-summary-row"><span>Delivery</span><b>{selected.offer.delivery_days ?? '—'} days</b></div>
            <div className="procurement-summary-row"><span>Trust signal</span><b className="money-positive">{Math.round(selected.score)} / 100</b></div>
            <div className={`procurement-alert ${overLimit ? 'warn' : 'good'}`}><span />{overLimit ? 'Human approval required: request exceeds the business spend limit.' : 'Within policy: eligible for agent execution.'}</div>
            <button className="economy-button economy-button-primary procurement-cta" disabled>{overLimit ? 'Request approval' : 'Purchase unavailable'}</button>
            <div className="procurement-disclaimer">Visa network · simulated purchase rail. No real funds moved.</div>
          </> : <div className="economy-empty compact">No purchase can be prepared until the backend returns a supplier offer.</div>}
        </aside>
      </section>
    </EconomyShell>
  );
}
