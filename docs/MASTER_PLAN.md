# NammaMove master plan
Authoritative sequence, superseding coarse numbering in PRODUCT_ROADMAP.md. That historical backlog is preserved. No additional prior strategy was present in the repository; this plan maps its requirements to the requested eleven phases.

## Product contract
Plan and recover feasible Bengaluru multimodal journeys. Missing GPS is uncertainty, not cancellation. Incident confidence, freshness and verification are distinct. Verify disruptions before live graph changes. Rerouting must account for aggregate congestion and capacity, not just an individual's fastest path.

## Phase sequence
- [Phase 00: Foundation and project setup](phases/PHASE_00.md)
- [Phase 01: Database and identity](phases/PHASE_01.md)
- [Phase 02: Bengaluru transit data](phases/PHASE_02.md)
- [Phase 03: Multimodal routing](phases/PHASE_03.md)
- [Phase 04: Mobile UI and web shell](phases/PHASE_04.md)
- [Phase 05: Live tracking and feed reliability](phases/PHASE_05.md)
- [Phase 06: Disruption verification and recovery](phases/PHASE_06.md)
- [Phase 07: Predictive AI and reliability](phases/PHASE_07.md)
- [Phase 08: Payments and ticketing](phases/PHASE_08.md)
- [Phase 09: Operations and resilience](phases/PHASE_09.md)
- [Phase 10: Deployment and pilot release](phases/PHASE_10.md)

## Progressive stack
00: Python/FastAPI/Pydantic, pytest/Ruff/mypy, Docker scaffolding and GitHub Actions.
01: PostgreSQL/PostGIS, SQLAlchemy/Alembic and Supabase Auth.
02: GTFS and GTFS-Realtime ingestion contracts and provenance.
03: OpenTripPlanner and approved GTFS/OSM graphs.
04: React Native + Expo and React with strict TypeScript.
05: Live GTFS-Realtime and Redis.
07: Python ML with scikit-learn and XGBoost.
10: Production Docker and hardened GitHub Actions CI/CD.
Only install dependencies when their phase needs them.

## Updated journey/wallet dependencies (2026-11-14; planned requirements)

The [PRD v1.1](PRD.md) and [architecture amendment](ARCHITECTURE.md#updated-journey-wallet-and-validation-design--planned) record the intended continuous Bengaluru journey across bus/metro/walk and partner-supported auto/cab/bikes. The unified wallet and one-QR dual-validation academic demonstration are required future scope, not current functionality.

| Phase | Additional intended scope | Gate |
|---|---|---|
| 05 | Feed reliability/durable provenance; owner-scoped JourneySession/JourneyLeg and authenticated mobile progress foundations | No financial execution or GPS-inferred completion; current focus remains synthetic ingestion reliability |
| 06 | Safe reachable-exit, preference/accessibility-preserving confirmed reroute; synthetic fare-aware revisions | Trusted evidence, user choice/cooldown and network-capacity tests; preserve tickets/incurred fares |
| 07 | Uncertain ETA and transfer-risk warnings | Calibrated held-out evaluation; prediction is not verification |
| 08 | Simulated wallet with configurable INR 500 minimum/affordability/holds; demo dual validation; approved booking, debit, refunds and separate settlement | Academic no-money/no-genuine-ticket boundary, then authorized partner/operator agreements and financial/validation tests |
| 09 | Validation disputes, provider failures, reconciliation and digital-twin resilience | Auditable operations, support/restore and retention evidence |
| 10 | Security, authorized integrations and limited Bengaluru pilot | All applicable provider/source/privacy/release gates; no deployment authorization here |

## Delivery policy
Each phase specifies prerequisites, tasks, deliverables, edge cases, tests and completion criteria. Update PHASE_STATUS.md with evidence. Configuring CI is not proof of a successful hosted run. Use licensed or synthetic fixtures; distinguish mock integration from live pilot validation. Cross-cutting safety gates remain release blockers.

## Engineering standards
Typed validated boundaries; versioned API/data contracts; migrations and transactions; role authorization; location consent/minimization/retention; secrets outside Git; accessibility and translation; bounded workloads and graceful fallback. Start with a modular monolith and integration adapters. Record material decisions in DECISIONS.md.

## Measurement
Track GPS-attributable false cancellation (target zero), incident precision, feed age, ETA interval calibration, transfer success, accessibility failures, oscillations and aggregate network load delta. Establish replay baselines before live use. Provisional p95 routing target is under 2 seconds; operations/release phases must validate availability and recovery budgets against measured pilot workloads.

## Current engineering boundary
Phase 01 is accepted locally: 45 tests pass with zero skips, including real PostgreSQL/PostGIS migrations/RLS/grants, backup/restore and genuine Supabase Auth. See PHASE_STATUS.md and DATABASE.md for scope and production limits. Phase 02 implements static catalog/import/search, with provider rights and authoritative coverage gates open. Phase 03 routing and Phase 04 clients remain bounded to their documented synthetic/acceptance scope. User-authorized Phase 05 engineering includes replay/protobuf adapters, atomic Redis event state, whole-feed ingestion, owner-registered durable evidence/static binding/restart watermarks, source-scoped non-owner workers, explicit scheduled bounded retention/recovery and bounded metadata dispatch of committed synthetic generations with durable leases/retries. Next is operational multi-source orchestration/global admission; raw-ingress durability and fetch remain separately gated. No live provider activation, authenticated delivery, wallet/QR or Phase 06. See [realtime](REALTIME.md), [durability boundary](DURABLE_INGESTION.md) and phase status.
