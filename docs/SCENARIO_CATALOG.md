# Scenario catalog
Stable IDs map expected outcomes to delivery/test ownership.

| ID | Scenario | Expected behavior | Phase | Evidence |
|---|---|---|---|---|
| S01 | Missing/stale GPS | Uncertain service with observed age; never infer cancellation | 00/05 | Engine and HTTP tests now |
| S02 | Authoritative cancellation | Retain independent authority and exclude affected service | 01/05 | Demo state test now; live trust tests planned |
| S03 | Delayed moving bus | ETA range and missed-transfer risk | 05/07 | Replay/calibration planned |
| S04 | Verified closure | Audited expiring overlay and feasible reroute | 00/06 | Demo block test now; expiry/authority planned |
| S05 | Unverified closure | Warn with confidence, never automatically close link | 00/06 | Demo tests now; moderation planned |
| S06 | Flood | Avoid verified unsafe walking links | 03/06 | Graph safety fixtures planned |
| S07 | Metro outage | Respect affected sequence and accessible station access | 03/06 | Timetable fixtures planned |
| S08 | Crowded alternative | Reject harmful aggregate load shifts | 00/06 | Static preference tested; load replay planned |
| S09 | No safe alternative | Explain limits and safe waiting/support choices | 03/06 | 404 tested; rider guidance planned |
| S10 | Spoofed GPS | Quarantine implausible telemetry | 05 | Replay planned |
| S11 | Feed/backend outage | Timestamped cache and clear availability | 04/05/09 | Outage tests planned |
| S12 | Offline/low battery | Cached itinerary and reduced refresh | 04/05 | Device tests planned |
| S13 | Replan oscillation | Cooldown and minimum benefit | 06 | State-machine replay planned |
| S14 | Report abuse | Rate limits, deduplication, audit, moderation | 06 | Adversarial tests planned |
| S15 | Lift unavailable | Only confirmed accessible paths | 03/06 | Accessibility fixture planned |
| S16 | Payment failure | No entitlement before verified success | 08 | Sandbox ledger tests planned |
| S17 | Concurrent disruptions | Combined constraints with bounded work | 06 | Multi-incident replay planned |
| S18 | Mid-vehicle diversion | Replan at reachable alighting point | 06 | Feasibility tests planned |
| S19 | Location permission denied | Manual stop selection without hidden tracking | 04 | Permission tests planned |
| S20 | Incident storm | Bound queues and target notifications | 09 | Burst tests planned |
| S21 | Overnight/holiday transit | Local calendar and times above 24:00 | 02/03 | GTFS fixtures planned |
| S22 | Forged identity/webhook | Reject unauthorized authority and ledger mutations | 01/08 | Security contracts planned |
| S23 | Negative GPS age | HTTP validation rejection | 00 | API test now |
| S24 | Duplicate reports/payments | Idempotent evidence and ledger transitions | 06/08 | Concurrency/replay planned |
