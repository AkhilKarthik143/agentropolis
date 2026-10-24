# Verification report — October 23, 2026

## Current result

**Backend: 77 tests pass.** The isolated local smoke passes twice, and a genuine local uAgents message exchange passes. **Current frontend acceptance is pending in the other UI chat.** The user confirmed a separate chat is actively redesigning the same frontend; its writes changed the source during this run. Earlier UI evidence is retained but is not evidence for the latest redesign.

| Check | Result / scope |
|---|---|
| `cd backend && python3 -m pytest -q` | 77 passed in 5.07 s, 3 upstream uAgents Python 3.14 deprecation warnings |
| `bash backend/scripts/demo_smoke.sh --full` | Two reset/recovery cycles pass; receipt, single settlement, entity reconciliation and WebSocket ordered reconnect pass |
| `cd backend && python3 scripts/verify_fetch.py` | Actual local uAgents dispatch between two distinct addresses; one typed message received; Agentverse explicitly false |
| Frontend build + lint, before concurrent redesign | Passed; 504.39 kB JS / 156.48 kB gzip, Vite chunk-size advisory |
| Browser suite, before concurrent redesign | 6 passed in 10.0 s at 1440×960 and 1180×820 |
| Phone route measurements after responsive repair | All six routes fit 390 px; screenshot retained; this preceded the concurrent redesign |
| Latest browser run during concurrent redesign | 2 passed, 6 failed: World did not render a main element; final UI owner must resolve/retest |
| Latest compiler during concurrent redesign | Failed on new animation component types; some targeted fixes applied, no final green build claimed |
| Docker | Configuration present; not run because Docker executable was unavailable |
| External Claude/Nessie/x402/Apify/public Fetch | Not verified; fixture/contract tests are not external evidence |

## Reproduce

Install dependencies using README. Run the backend suite from `backend/`. Start the app with `./scripts/dev.sh`. From `frontend/`, run `npm run build`, `npm run lint`, and `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5176 npm run test:e2e`, replacing the port with the actual Vite port. Browser tests use installed Google Chrome, one worker, and the local API proxy. They reset the demo and create Browser QA businesses; use a disposable local data directory for test runs.

The final UI suite has eight cases including two project variants of the 390 px route check. Screenshots in `evidence/` are from the earlier six-case passing snapshot; Playwright traces for failures are ignored local output under `frontend/test-results/`.

## Backend coverage

- Durable queue expiry, leases, retry/backoff/dead-letter, duplicate delivery and restart.
- Different buyer objectives, independent supplier state/quotes/counteroffers, no feasible recovery, actual recovery negotiation.
- Accepted contract does not deliver or pay; partial receipt blocks payment.
- Supplier reservations, available quantity, cost floor, multiple outstanding cash commitments.
- Separate buyer/seller double-entry journals; one-sided entity imbalance rejected.
- Concurrent SQLite engine instances cannot oversell stock or repeat payment.
- Repeated settlement, failed payment/retry and uncertain payment/no resubmission.
- Exact approved proposal terms, session/agent scope, strict cents and quantities.
- Snapshot/event rollback together and state restoration after restart.
- Optional roles: missing manager blocks recovery, missing payments prevents settlement, missing accounting prevents automatic reconciliation and catches up after reenable.
- Nested private agent notes excluded from public runtime and event projections.
- Independent session speeds, persistence reload, isolation, partial API receipt and reset stream reconnection.
- Provider HTTP contracts and guarded signing/submission behavior using explicit fixtures.

## Local timing sample

Python 3.14.7; five fresh in-memory worlds of ten businesses, each supplier failure plus four ticks: 0.1745, 0.1735, 0.1731, 0.1866, 0.1754 seconds; median 0.1745 s. Final world contained 113 deployed role instances and 391 events. One summary projection took 0.0051 s and serialized to 198,426 bytes. This is a small local timing sample, not a production load benchmark. Full snapshot/history projections, multiple autonomous workers, sustained frame rate and large-company scaling need dedicated tests.

## Limits

No fresh-machine install, Docker execution, multi-browser matrix, formal accessibility audit, external-provider outage/load test, public deployment or testnet payment was completed. At-least-once message processing does not mean exactly-once arbitrary external side effects. Existing legacy data may contain prior public payloads; reset/checkpoint rather than rewriting the audit chain when preparing a clean demo.
