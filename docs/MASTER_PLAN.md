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

## Delivery policy
Each phase specifies prerequisites, tasks, deliverables, edge cases, tests and completion criteria. Update PHASE_STATUS.md with evidence. Configuring CI is not proof of a successful hosted run. Use licensed or synthetic fixtures; distinguish mock integration from live pilot validation. Cross-cutting safety gates remain release blockers.

## Engineering standards
Typed validated boundaries; versioned API/data contracts; migrations and transactions; role authorization; location consent/minimization/retention; secrets outside Git; accessibility and translation; bounded workloads and graceful fallback. Start with a modular monolith and integration adapters. Record material decisions in DECISIONS.md.

## Measurement
Track GPS-attributable false cancellation (target zero), incident precision, feed age, ETA interval calibration, transfer success, accessibility failures, oscillations and aggregate network load delta. Establish replay baselines before live use. Provisional p95 routing target is under 2 seconds; operations/release phases must validate availability and recovery budgets against measured pilot workloads.

## Current Phase 01 boundary
Phase 01 is accepted locally: 45 tests pass with zero skips, including real PostgreSQL/PostGIS migrations/RLS/grants, backup/restore and genuine Supabase Auth. See PHASE_STATUS.md and DATABASE.md for scope and production limits. No Phase 02 imports or later-phase routing/live features have started.
