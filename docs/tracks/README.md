# Sponsor track guides

These guides are implementation plans grounded in the current standalone source.
They are not eligibility claims. The exact Cal Hacks/event brief, deadlines,
submission rules, and sponsor APIs must be verified before a track is described as
submission-ready.

## Status vocabulary

`NOT_STARTED` means no implementation exists. `DESIGNED` means architecture or a
seam is documented. `IMPLEMENTED_UNTESTED` means code exists without adequate
evidence. `MOCK_TESTED` means offline fixtures pass. `LOCAL_VERIFIED` means a real
local/runtime workflow passed. `EXTERNAL_VERIFIED` means the configured sponsor
service actually responded successfully. `DEMO_READY` means the exact workflow is
rehearsed and evidence is captured. `BLOCKED` means a specific external or human
dependency prevents progress.

No track should be upgraded based on a folder, a fixture, or a sponsor name in a
README. Update [sponsor-matrix](../sponsor-matrix.md), the track README, and the
final-readiness report together when evidence changes.

| Track | Guide | Current status | Primary blocker |
| --- | --- | --- | --- |
| Hyphenate | [guide](hyphenate/README.md) | LOCAL_VERIFIED product workflow | Official challenge requirements; no API claim |
| Coinbase Payment Agents | [guide](coinbase/README.md) | MOCK_TESTED | Approved Base Sepolia resource/wallet and service-expense integration |
| Visa | [guide](visa/README.md) | LOCAL_VERIFIED product workflow | Official API/track requirements |
| Capital One Nessie | [guide](capital-one/README.md) | MOCK_TESTED | Sandbox key/account and evidence run |
| CRS Credit | [guide](crs-credit/README.md) | MOCK_TESTED | Official sandbox contract and test identities |
| Solana | [guide](solana/README.md) | NOT_STARTED | Official API/wallet and approved devnet workflow |
| Fetch.ai | [guide](fetch-ai/README.md) | LOCAL_VERIFIED | Public Agentverse registration/reachability |
| Creao | [guide](creao/README.md) | NOT_STARTED | Platform capability and access confirmation |
| SpacetimeDB | [guide](spacetimedb/README.md) | DESIGNED | Product authority/consistency decision and deployment |
