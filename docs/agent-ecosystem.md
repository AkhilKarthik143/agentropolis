# Agent ecosystem

The current implementation is documented in [agent architecture](agent-architecture.md), with all 18 role types, permission boundaries, durable queue semantics, and limitations. [Workflows](workflows.md) describes the end-to-end lifecycle and [domain model](domain-model.md) defines its economic records.

The core sequence is:

```text
Inventory need → Manager task → Procurement RFQs
                                  ↕
                   Independent supplier quotes/counteroffers
                                  ↓
                  Negotiation → Treasury + Risk → Payments role
                                  ↓
                          Trusted engine validation
                                  ↓
                  Reserve → Ship → Receive → Match invoice
                                  ↓
                            Pay → Reconcile
```

Contract acceptance reserves stock. It does not create a receipt, settle cash, or declare a recovery successful. The default environment uses simulated physical delivery and banking, with a durable event trail exposing each separate step.
