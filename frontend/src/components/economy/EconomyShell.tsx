import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, Banknote, GitBranch, Hexagon, Landmark, Radio, ShoppingCart, Sparkles, Store, Zap } from 'lucide-react';
import { AnimatePresence, MotionConfig, motion } from 'motion/react';
import { motionTokens } from '@/lib/motion';

const moneyFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const eventTimeFormatter = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' });

const navItems = [
  { href: '/economy/world', label: 'The World', icon: Hexagon },
  { href: '/economy/negotiations', label: 'Negotiations', icon: GitBranch },
  { href: '/economy/control-tower', label: 'Control tower', icon: Landmark },
  { href: '/economy/procurement', label: 'Procurement', icon: ShoppingCart },
  { href: '/economy/businesses', label: 'Businesses', icon: Store },
  { href: '/economy/scenarios', label: 'Shock engine', icon: Zap },
];

export function EconomyShell({ children, title, eyebrow, connected, actions }: { children: ReactNode; title: string; eyebrow: string; connected: boolean; actions?: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
    <div className="economy-theme min-h-svh">
      <a className="economy-skip-link" href="#economy-main">Skip to main content</a>
      <aside className="economy-sidebar">
        <div className="economy-brand">
          <div className="economy-logo"><Sparkles size={15} aria-hidden="true" /></div>
          <div><div className="economy-brand-name">Agentropolis</div><div className="economy-brand-sub">Autonomous economy</div></div>
        </div>
        <div className="economy-live"><span className={connected ? 'live-dot live-dot-on' : 'live-dot'} />{connected ? 'Live event stream' : 'Reconnecting…'}</div>
        <nav className="economy-nav" aria-label="Agentropolis">
          {navItems.map(({ href, label, icon: Icon }) => <NavLink key={href} to={href} aria-label={label} className={({ isActive }) => `economy-nav-link ${isActive ? 'active' : ''}`}><Icon size={16} aria-hidden="true" /><span>{label}</span>{label === 'Shock engine' && <span className="economy-nav-count" aria-label="6 scenarios">6</span>}</NavLink>)}
        </nav>
        <div className="economy-sidebar-bottom">
          <div className="economy-rail-caption">Execution environment</div>
          <div className="economy-sponsor-row"><Radio size={14} aria-hidden="true" /> Local agent transport</div>
          <div className="economy-sponsor-row"><Banknote size={14} aria-hidden="true" /> Simulated bank rail</div>
          <NavLink to="/economy/world" className="economy-back-link">Return to Agentropolis home</NavLink>
        </div>
      </aside>
      <main id="economy-main" className="economy-main">
        <header className="economy-header">
          <div><div className="economy-eyebrow">{eyebrow}</div><h1>{title}</h1></div>
          <div className="economy-header-actions">{actions}<div className="economy-mode-badge"><Activity size={13} /> SIMULATION</div></div>
        </header>
        {children}
      </main>
    </div>
    </MotionConfig>
  );
}

export function Money({ cents, signed = false }: { cents: number; signed?: boolean }) {
  const prefix = cents < 0 ? '-' : signed && cents > 0 ? '+' : '';
  return <span className={cents < 0 ? 'money-negative' : cents > 0 && signed ? 'money-positive' : ''}>{prefix}${moneyFormatter.format(Math.abs(cents / 100))}</span>;
}

export function StatusPill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' }) {
  return <span className={`economy-status economy-status-${tone}`}><span aria-hidden="true" />{children}</span>;
}

export function EventRail({ events, limit = 8 }: { events: { seq: number; type: string; ts: string; payload: Record<string, unknown> }[]; limit?: number }) {
  return <div className="economy-event-rail" role="log" aria-live="polite" aria-label="Economy event stream"><AnimatePresence initial={false} mode="popLayout">{events.slice(-limit).reverse().map((event) => <motion.div className="economy-event-row" layout key={event.seq} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transform: 'translateY(-4px)' }} transition={{ duration: motionTokens.duration.standard, ease: motionTokens.ease.out }}><div className="economy-event-seq">{String(event.seq).padStart(3, '0')}</div><div><div className="economy-event-type">{event.type}</div><div className="economy-event-time">{eventTimeFormatter.format(new Date(event.ts))}</div></div></motion.div>)}</AnimatePresence></div>;
}

