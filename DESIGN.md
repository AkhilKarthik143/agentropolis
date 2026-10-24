# Agentropolis design system

## Creative direction

**Neon cartography meets editorial science fiction.** Dark architectural surfaces, luminous pathways, abstract geometry, beautiful typography, and carefully controlled colors. The interface is a generative-art experience built around a functioning autonomous economy — not a conventional SaaS dashboard.

## Motion design system

Single source of truth: `frontend/src/lib/motion-design-system.ts` — timing, easing, springs, and performance tiers (high / balanced / minimal). Every animation layer references these tokens.

Five motion layers:
1. **Ambient** — slow constellation, procedural grid, logo rotation, idle breaths
2. **Interactive** — hover, selection, pan/zoom, page transitions, button states
3. **Data-driven** — backend events drive particles, node pulses, connection changes
4. **Cinematic** — economic shock sequences (bankruptcy, demand spike, liquidity crisis, fraud detection)
5. **Generative** — procedural grid distortion reflecting market health

Central coordinator: `frontend/src/lib/motion-coordinator.ts` — event-ID/sequence-number deduplication, replay support, tier-based effect gating.

## Visual identity

- **AgentropolisLogo** (`frontend/src/components/visual-identity/AgentropolisLogo.tsx`) — original geometric constellation mark forming an abstract "A" with luminous pathways and orbiting indicators
- **AgentAvatars** (`frontend/src/components/visual-identity/AgentAvatars.tsx`) — 13 abstract agent identities: manager (crown), procurement (orbital scan), negotiation (intersecting forms), treasury (concentric rings), risk (shield), accounting (interlocking entries), recovery (fragmented→stable), strategy (rotating data structure), credit, auditor, market intelligence, inventory, supplier
- **BusinessNode** (`frontend/src/components/economy/BusinessNode.tsx`) — industry-specific procedural motifs: bank (vault), logistics (directional pathways), retail (storefront), research (rotating data structure), supplier (inventory indicators), default (constellation)
- **AnimatedConnection** (`frontend/src/components/economy/AnimatedConnection.tsx`) — flowing light paths with animated message packets, color-coded statuses, activity-based thickness, path-drawing on formation, dissolving on expiry
- **EconomicConstellation** (`frontend/src/components/ambient/EconomicConstellation.tsx`) — Canvas 2D slow-moving particle constellation that flashes on real economic events
- **ProceduralGrid** (`frontend/src/components/ambient/ProceduralGrid.tsx`) — Canvas 2D grid distortion with cursor parallax and market-health color modulation
- **EconomicParticles** (`frontend/src/components/ambient/EconomicParticles.tsx`) — Canvas 2D particle flows for financial transactions between business nodes
- **CinematicShockOverlay** (`frontend/src/components/economy/CinematicShockOverlay.tsx`) — full-screen choreographed sequences for supplier bankruptcy, demand spike, liquidity crisis, fraud detection, recovery

## Pages

- **WorldPage** (`frontend/src/pages/WorldPage.tsx`) — Living Economy: constellation of businesses with animated connections, particle flows, ambient background, agent teams, event rail
- **NegotiationRoomPage** (`frontend/src/pages/NegotiationRoomPage.tsx`) — Animated supplier comparison, negotiation timeline, offer lanes, counteroffer visualization
- **ControlTowerPage** (`frontend/src/pages/ControlTowerPage.tsx`) — Financial control tower with smooth balance transitions, payment status animations (proposed→processing→confirmed→failed→reconciled), ledger motion
- **ProcurementPage** (`frontend/src/pages/ProcurementPage.tsx`) — Animated supplier discovery, dynamic offer comparison, price/delivery tradeoff visualization
- **ScenariosPage** (`frontend/src/pages/ScenariosPage.tsx`) — Shock injection with cinematic overlays, cause→effect trace, replay audit

## Animation inventory

`docs/animation-inventory.md` — tracks every implemented animation with screen, trigger, component, technology, layer, event source, duration, reduced-motion behavior, performance cost, and verification status. Target: 60+ distinct patterns.

## Rendering stack

- **framer-motion (motion)** — React animations, shared-layout transitions, springs
- **Canvas 2D** — constellation, procedural grid, economic particles
- **SVG** — agent avatars, business node motifs, connections
- **CSS** — ambient glows, gradients, keyframe animations

No WebGL, Three.js, or React Three Fiber — Canvas 2D + SVG deliver the desired result with minimal bundle impact.

## Performance

- Adaptive tiers: high (full effects), balanced (reduced particles), minimal (transitions only)
- Reduced motion respected via `prefers-reduced-motion` and `useReducedMotion()`
- Nonessential animation pauses when page is hidden
- Event deduplication by sequence number and event ID prevents duplicate visual events

## Testing

Playwright tests in `frontend/tests/` — 14 passing tests covering navigation, all major screens, reduced motion, agent avatars, business node interaction, and screenshots.

## Existing Paper design

[Agentropolis Paper file](https://app.paper.design/file/01M5N52WWBCWZ1WT6AZEVH2Z8R) contains editable pages for design system, living economy, negotiations, finance, business detail, shocks, procurement, and motion. Code-based animation tooling implements live motion; static Paper designs are reference only.

## Backend

All existing backend functionality preserved. Frontend reads real economy events via WebSocket (`/ws/simulations/demo_001`) and REST (`/api/simulations/demo_001`). Motion coordinator is never authoritative over financial state.
