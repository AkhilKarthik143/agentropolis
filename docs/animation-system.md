# Motion contract

> Handoff note: the user confirmed a concurrent UI redesign on October 23. Descriptions and screenshots below document the earlier verified UI snapshot; recheck against the final UI chat output. See docs/testing.md (testing.md from within docs).
`frontend/src/lib/motion.ts` defines 140/180/220/280/620 ms durations and shared ease-out curves. `MotionConfig reducedMotion="user"` is applied by the shell.

| Component | Purpose / trigger | Reduced motion |
|---|---|---|
| AnimatedGroup | Enter small related card groups | No hidden initial state or stagger |
| AnimatedNumber | Interpolate a confirmed displayed value | Direct value text |
| TransitionPanel | Context changes without losing position | Reduced transform/duration |
| ReactBitsBlurText | One world headline entrance | Static readable text |
| MagicAnimatedBeam / graph marker | Illustrate a recorded relationship/event | Motion removed or zero duration |
| EventRail | New committed events enter in sequence | User preference through MotionConfig |
| Offer cards | Quote additions/reordering | No entrance transform |
| Approval rows | Remove resolved requests | No animated exit under preference |

Motion never submits a payment, creates a contract, delays an approval, or proves success. The application shows only committed engine results. No fake activity timer feeds monetary totals. Graph markers map to actual payment/offer events and their deal IDs. The cash sparkline is derived from cash journal postings.

The event hook caps visible history at 600, debounces summary refresh to 180 ms, resumes using event sequence and responds to resync. Graph and event rail are bounded views; full server history and runtime summaries are not yet paginated, and expensive projection work will need optimization at larger scale. Production bundle size is recorded in testing.md; sustained 60 fps is not claimed.
