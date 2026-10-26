# Phase 03 - Multimodal routing

Status: implemented and verified for independently authored synthetic fixtures; real Bengaluru/pilot acceptance remains blocked. The user's explicit Phase 03 request authorizes this local engineering scope while preserving Phase 02 external-data blockers. No Phase 04, commit, push or merge.

## Prerequisites and scope
- [x] Actual OTP parses the independently authored GTFS and authorized CC0 geographic-grid inputs; no third-party transport/street rows imported.
- [x] Declared local engineering budget: two CPUs, 3 GiB container memory, 2 GiB Java heap, four concurrent API requests.
- [x] Existing Phase 00-02 contracts/regressions retained; database schema remains at `0002_transit_data`.
- [ ] Phase 02 real-provider rights, authoritative current coverage and schedule/geographic/accessibility certification remain unresolved.
- [ ] Real-pilot resource sizing, agency access, operational accessibility and production approval remain open.

## Implementation tasks and deliverables
- [x] Official OTP 2.7.0 image pinned by digest/platform; separate Compose build/serve project and no-network builder.
- [x] Deterministic owned GTFS/PBF fixture generator, versioned input hashes, graph artifact sealing/integrity checks, source-metadata cross-checks and explicit previous-release rollback.
- [x] Typed GraphQL `planConnection` adapter and authenticated `/v1/routing/plan` with a versioned request/itinerary contract.
- [x] Bus, metro, source street walking, transfers, weekdays/date exceptions, reverse direction, overnight runs, transit-only/mode, walking/transfer limits and source wheelchair constraints.
- [x] Departure/arrival-time planning, UTC/local conversion and strict actual-deadline post-validation. A documented OTP boundary false negative uses bounded candidate padding; no late arrival is returned.
- [x] Fastest/cheapest/fewest-transfer/least-walking ranking within bounded provider candidates; source fixture fares/null unknown fares, attribution, explicit data confidence and journey explanations.
- [x] Separate scheduled physical duration, initial waiting and elapsed-from-requested-departure; no generalized cost added to ETA.
- [x] Bounded concurrency/query/response work, sanitized 503/409/422 failures, no-route explanations and no silent simulator/stale-graph fallback.
- [x] Provider protocol and graph/trip/direction/time metadata for future updates; no client-authorized incident overlay or live worker.
- [x] Real OTP contracts/integration/load tests, genuine Supabase-authenticated API benchmark, source-free fixtures and CI build/test configuration.

Deliverables: [routing package](../../backend/app/routing/), [Compose](../../compose.routing.yaml), [recorded fixture contract](../../backend/tests/fixtures/otp/), [routing runbook](../ROUTING.md), [acceptance evidence](../evidence/phase03-routing.json), tests and updated architecture/decisions/status/feature/scenario records.

## Edge cases and automated tests
Missed connection/last service, holiday removal, previous service-day midnight trip, reverse direction, same/unknown stop, invalid coordinate/timezone/modes, zero walking allowance, unknown/inaccessible wheelchair source flags, missing fare, disconnected/out-of-bounds geography, unavailable or saturated provider, malformed/oversized/inconsistent GraphQL response, graph mismatch/corruption and metadata tampering.

Portable tests replay an actual OTP response over owned inputs and use mocks only for failure boundaries. Actual OTP tests verify feasible bus-walk-metro transfers, alternative preferences, directions/calendars/night runs, arrival deadlines, walking/accessibility constraints and bounded load. The full-API benchmark uses genuine local Supabase tokens/JWKS and the existing non-owner DB configuration with no Auth/database/provider override. Real PostGIS and Phase 00-02 tests remain enabled in the complete acceptance run. Latest measured counts/timings are in [PHASE_STATUS.md](../PHASE_STATUS.md).

## Completion criteria and measured scope
| Criterion | Result |
|---|---|
| Fixture journeys feasible | Actual OTP bus-walk-metro plan: 08:00-08:17; valid transfer walking/buffer, 30 authored INR total; alternatives and arrival/departure constraints tested |
| ETA excludes artificial penalties | Physical duration 1,020 seconds; initial wait 300 seconds from 07:55 request; elapsed-to-arrival 1,320 seconds; verified separately from preference ranking |
| p95 under two seconds at declared load | Passed for 40 warm authenticated API requests with four concurrent callers on declared fixture resources; exact timing/hashes in evidence |
| Outages degrade clearly | Real OTP stop returns 503; restart recovers with identical artifact; no legacy-simulator substitution; previous-release and graph-conflict checks passed |
| Reproducible graph inputs/pipeline | Canonical input files, pinned image/platform, input-derived identity and recorded actual artifact hash; successful real build/load; binary serialization identity is not promised |
| Full real-network/pilot acceptance | Not met: Phase 02 external prerequisites, current operational accessibility, city-scale/pilot validation and production hardening unresolved |

**Documented fixture-level functional/performance criteria are met at the declared local test load. This does not accept full Phase 02 or claim real Bengaluru/pilot readiness.** The original unqualified phase prerequisite is satisfied only within the user-authorized synthetic scope; real-provider gates remain open.

## Known limitations and safety gate
- Preferences rank at most sixteen returned candidates; no exhaustive global optimality guarantee. Walking limits can post-filter all returned candidates even if an unreturned route exists.
- OTP 2.7 arrival-boundary padding is a bounded workaround, not exhaustive arrival search certification. Inactivity timeouts do not cancel every server-side search; cold load/JIT is excluded from steady-state SLA and may return 503 while becoming ready.
- Explicit coordinated operator rollback/restart; no remote binary attestation, automatic failover or zero-downtime deployment controller. Verify matching backend/OTP release directories and canary before switching.
- Known fixture fares are integer INR per boarding only; no general fare product/zone/pass engine, payments or real agency quote.
- Authored walking/wheelchair data is not surveyed accessibility or live lift status. Data is simulation, realtime unavailable, service status unknown. Missing GPS never means cancellation.
- No trusted live disruption changes, automatic rerouting, network assignment or aggregate congestion safety claim. Those require later phase gates and network impact testing.
- Hosted CI, Linux/Python 3.12 backend execution, real-pilot load and production security/support review of the pinned release remain unverified locally.

See [ROUTING.md](../ROUTING.md) for commands, contract/failure details, privacy, lifecycle and scope.
