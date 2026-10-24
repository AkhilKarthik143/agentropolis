# Agentropolis Animation Inventory

Central registry of every implemented animation, its location, trigger, and performance cost.
Target: 60+ distinct meaningful patterns.

## How to read

- **ID**: Unique animation identifier
- **Screen**: Where it appears
- **Trigger**: What causes it (user action, backend event, ambient)
- **Component**: React component that renders it
- **Technology**: framer-motion / svg / canvas / css
- **Layer**: ambient / interactive / data-driven / cinematic / generative
- **Event source**: Backend event type (if data-driven)
- **Duration**: Approximate seconds
- **Reduced motion**: Behavior under `prefers-reduced-motion`
- **Performance**: low / medium / high
- **Status**: implemented / planned

---

## Layer 1 — Ambient (slow, subtle, always-on)

| ID | Screen | Trigger | Component | Tech | Layer | Duration | Reduced motion | Perf | Status |
|----|--------|---------|-----------|------|-------|----------|----------------|------|--------|
| A01 | World | Page load | EconomicConstellation | canvas | ambient | Continuous | Static nodes | low | implemented |
| A02 | World | Page load | ProceduralGrid | canvas | ambient | Continuous | Static grid | low | implemented |
| A03 | World | Page load | AgentAvatar idle breath | svg | ambient | 4s loop | Disabled | low | implemented |
| A04 | World | Page load | Business node orbiting indicators | svg | ambient | 4-5s loop | Disabled | low | implemented |
| A05 | World | Page load | Business node pulse ring | svg | ambient | 2-3s loop | Disabled | low | implemented |
| A06 | World | Page load | Industry motif animation (bank vault, logistics path, etc.) | svg | ambient | 2-5s loop | Disabled | low | implemented |
| A07 | All | Page load | Agentropolis logo rotation | svg | ambient | 20s loop | Disabled | low | implemented |
| A08 | All | Page load | Agentropolis logo pulse | svg | ambient | 4s loop | Disabled | low | implemented |
| A09 | All | Page load | Gradient text rainbow shift | css | ambient | 5s loop | Disabled | low | implemented |
| A10 | All | Page load | Mesh glow orbs | css | ambient | Continuous | Disabled | low | implemented |

## Layer 2 — Interactive (hover, click, drag, select, navigate)

| ID | Screen | Trigger | Component | Tech | Layer | Duration | Reduced motion | Perf | Status |
|----|--------|---------|-----------|------|-------|----------|----------------|------|--------|
| I01 | World | Node hover | BusinessNode scale + label | framer-motion | interactive | 0.2s | Instant | low | implemented |
| I02 | World | Node select | BusinessNode scale up + highlight | framer-motion | interactive | 0.3s | Instant | low | implemented |
| I03 | World | Pan/drag | Map container translate | css | interactive | Continuous | Same | low | implemented |
| I04 | World | Zoom | Map container scale | css | interactive | 0.2s | Instant | low | implemented |
| I05 | World | Clock control button | Button press state | css | interactive | 0.15s | Instant | low | implemented |
| I06 | Negotiation | Offer card hover | Card lift + border | css | interactive | 0.2s | Instant | low | implemented |
| I07 | Negotiation | Offer card select | Card selected state | framer-motion | interactive | 0.2s | Instant | low | implemented |
| I08 | Negotiation | Thread select | List item highlight | framer-motion | interactive | 0.2s | Instant | low | implemented |
| I09 | Control Tower | Treasury selector | Select field animation | css | interactive | 0.2s | Instant | low | implemented |
| I10 | Control Tower | Payment status change | Status pill color transition | css | interactive | 0.3s | Instant | low | implemented |
| I11 | Control Tower | Ledger row hover | Row highlight | css | interactive | 0.2s | Instant | low | implemented |
| I12 | Procurement | Supplier card hover | Card lift + shadow | css | interactive | 0.2s | Instant | low | implemented |
| I13 | Procurement | Supplier card select | Selected state | framer-motion | interactive | 0.3s | Instant | low | implemented |
| I14 | Scenarios | Shock card hover | Card lift + border | css | interactive | 0.2s | Instant | low | implemented |
| I15 | All | Nav link hover | Sidebar link highlight | css | interactive | 0.2s | Instant | low | implemented |
| I16 | All | Page transition | Shell content fade | framer-motion | interactive | 0.28s | Instant | low | implemented |
| I17 | All | Skip link focus | Skip link slide down | css | interactive | 0.16s | Instant | low | implemented |
| I18 | All | Button active | Button press transform | css | interactive | 0.15s | Instant | low | implemented |

## Layer 3 — Data-driven (real backend events)

| ID | Screen | Trigger | Component | Tech | Layer | Event source | Duration | Reduced motion | Perf | Status |
|----|--------|---------|-----------|------|-------|--------------|----------|----------------|------|--------|
| D01 | World | PaymentConfirmed | Payment particle flow | canvas | data-driven | PaymentConfirmed | 1.2s | Particles off | medium | implemented |
| D02 | World | PaymentRecorded | Payment particle flow | canvas | data-driven | PaymentRecorded | 1.2s | Particles off | medium | implemented |
| D03 | World | Constellation flash on event | EconomicConstellation flash | canvas | data-driven | Any economy event | 0.5s | Disabled | low | implemented |
| D04 | World | SupplierDefaulted | Node disrupted state + shake | svg + framer-motion | data-driven | SupplierDefaulted | Continuous | Disabled | low | implemented |
| D05 | World | DeliveryFailed | Node disrupted state + shake | svg + framer-motion | data-driven | DeliveryFailed | Continuous | Disabled | low | implemented |
| D06 | World | ShockInjected | Cinematic flash + shake | framer-motion | cinematic | ShockInjected | 0.8s | Disabled | low | implemented |
| D07 | Negotiation | OfferReceived | Offer card stagger-in | framer-motion | data-driven | OfferReceived | 0.3s/card | Instant | low | implemented |
| D08 | Negotiation | CounterOfferReceived | Offer card update | framer-motion | data-driven | CounterOfferReceived | 0.3s | Instant | low | implemented |
| D09 | Negotiation | ContractAccepted | Connection forming | svg | data-driven | ContractAccepted | 0.8s | Instant | low | implemented |
| D10 | Control Tower | PaymentSubmitted | Payment record appears | framer-motion | data-driven | PaymentSubmitted | 0.3s | Instant | low | implemented |
| D11 | Control Tower | PaymentConfirmed | Payment confirmed styling | css | data-driven | PaymentConfirmed | 0.3s | Instant | low | implemented |
| D12 | Control Tower | PaymentFailed | Payment failed styling | css | data-driven | PaymentFailed | 0.3s | Instant | low | implemented |
| D13 | Control Tower | Reconciled | Ledger row balanced state | framer-motion | data-driven | Reconciled | 0.3s | Instant | low | implemented |
| D14 | Control Tower | LedgerPosted | Ledger row appears | framer-motion | data-driven | LedgerPosted | 0.25s | Instant | low | implemented |
| D15 | Control Tower | InvoiceMatched | Match status update | css | data-driven | InvoiceMatched | 0.3s | Instant | low | implemented |
| D16 | Control Tower | ApprovalRequested | Approval row appears | framer-motion | data-driven | ApprovalRequested | 0.25s | Instant | low | implemented |
| D17 | Control Tower | ApprovalGranted/Denied | Approval row removed | framer-motion | data-driven | ApprovalGranted/Denied | 0.25s | Instant | low | implemented |
| D18 | World | BusinessRegistered | Node appears | framer-motion | data-driven | BusinessRegistered | 0.4s | Instant | low | implemented |
| D19 | World | ContractAccepted | Connection appears | svg | data-driven | ContractAccepted | 0.8s | Instant | low | implemented |
| D20 | Procurement | Offer list update | Supplier cards emerge | framer-motion | data-driven | Offer list change | 0.3s/card | Instant | low | implemented |

## Layer 4 — Cinematic (major economic events)

| ID | Screen | Trigger | Component | Tech | Layer | Duration | Reduced motion | Perf | Status |
|----|--------|---------|-----------|------|-------|----------|----------------|------|--------|
| C01 | Scenarios | Supplier bankruptcy injected | Shock flash + node fracture | framer-motion + svg | cinematic | 2.0s | Disabled | medium | planned |
| C02 | Scenarios | Demand spike injected | Grid intensification | canvas | cinematic | 3.0s | Disabled | medium | planned |
| C03 | Scenarios | Liquidity crisis | Reserve warning pulse | framer-motion | cinematic | 2.0s | Disabled | low | planned |
| C04 | Scenarios | Fraud detection | Risk agent activation | svg | cinematic | 1.5s | Disabled | low | planned |
| C05 | Scenarios | Recovery sequence | New connection forming | svg | cinematic | 2.5s | Disabled | medium | planned |
| C06 | World | Shock response | Full-screen flash | framer-motion | cinematic | 0.8s | Disabled | low | implemented |

## Layer 5 — Generative (procedural, reflects economic conditions)

| ID | Screen | Trigger | Component | Tech | Layer | Duration | Reduced motion | Perf | Status |
|----|--------|---------|-----------|------|-------|----------|----------------|------|--------|
| G01 | World | Market health change | Grid distortion intensity | canvas | generative | Continuous | Static | low | implemented |
| G02 | World | Market health change | Grid color shift (teal→amber) | canvas | generative | Continuous | Static | low | implemented |
| G03 | World | Cursor movement | Grid cursor parallax | canvas | generative | Continuous | Disabled | low | implemented |
| G04 | World | Economic event | Constellation node brightening | canvas | generative | 0.5s | Disabled | low | implemented |

---

## Summary

- **Implemented**: 30 animations
- **Planned**: 6 animations (cinematic event sequences)
- **Total**: 36 distinct patterns

**Coverage by layer**:
- Ambient: 10
- Interactive: 18
- Data-driven: 20
- Cinematic: 1 (implemented) + 5 (planned)
- Generative: 4

**Technology breakdown**:
- framer-motion: 20
- svg: 8
- canvas: 4
- css: 8

**Performance**: 28 low, 2 medium, 0 high

**Reduced motion**: All animations respect `prefers-reduced-motion` with instant or disabled fallbacks.

---

## Next additions (to reach 60+)

1. Negotiation counteroffer traveling animation between agent identities
2. Price smooth update animation when offers change
3. Supplier ranking rearrangement with shared-layout transitions
4. Contract terms progressive reveal
5. Selected offer moving to final contract panel
6. Rejected proposal collapsing to history
7. Contract confirmation transition
8. Bank account selection animation
9. Smooth balance change transitions
10. Transaction entries arriving in activity feed
11. Fluid cash-flow visualization
12. Animated cash-reserve threshold
13. Interactive financial charts with smooth transitions
14. Ledger rows expanding into detailed journal entries
15. Payment status transformation
16. Risk alert appearance
17. Reconciliation sequence
18. Animated supplier discovery
19. Dynamic offer comparison graphics
20. Price/delivery tradeoff visualization
21. Shopping-to-negotiation transition
22. Recommendation reveal with evidence
23. Purchase approval animated dialog
24. Contract creation visual transformation
25. Supplier bankruptcy fracture animation
26. Demand spike energy wave
27. Supply bottleneck visibility
28. Liquidity crisis contracting paths
29. Fraud detection isolation
30. Risk agent activation sequence
31. Recovery agent morph animation
32. Agent activation sequence
33. Agent searching animation
34. Agent communication pulse
35. Agent morphing expression
36. Agent completion transformation
37. Agent error state
38. Agent handoff animation
39. Connection forming path-drawing
40. Connection dissolving
41. Connection thickness animation
42. Network ripple during transaction
43. Supply chain highlighting
44. Node health halo animation
45. Node color transformation during disruption
46. Node morphing on status change
47. Node expansion to detail panel
48. Particle burst on partnership
49. Loading state illustration animation
50. Empty state artwork animation
51. Page transition choreography
52. Magnetic button effect
53. Cursor-responsive element
54. Morphing navigation indicator
55. Sidebar transition
56. Contextual panel transition
57. Animated command menu
58. Interactive tooltip
59. Hover preview
60. Kinetic onboarding sequence
