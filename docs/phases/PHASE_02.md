# Phase 02 - Bengaluru Transit Data and Network Integration

Status: Implementation verified locally; full acceptance pending external source/coverage gates. Phase 03 is not started. No automatic commit, push or merge.

## Prerequisites
- [x] Phase 01 accepted locally; real PostGIS and genuine Supabase Auth are available.
- [x] Documented source register, pinned community BMRCL ODbL basis and explicit estimation caveats.
- [ ] Reviewed BMTC content rights/authorization and an accepted representative BMTC dataset.
- [ ] Authoritative current Bengaluru coverage/quality review across bus, metro and interchanges.

## Implementation tasks and deliverables
- [x] Add snapshot-scoped GTFS agencies, stops, routes, trips, stop times, calendars, exceptions, shapes, transfers and frequencies without changing Phase 00/01 contracts.
- [x] Bounded validation/normalization including opaque IDs, Kolkata service dates, overnight hours, references, duplicates, shape distances, directions and frequency windows.
- [x] Mandatory provenance/license/authorization/timestamps/checksums, immutable versions, staged imports, sanitized quarantine reports and same-feed rollback.
- [x] Atomic transaction promotion and per-feed PostgreSQL advisory locks; concurrent identical imports are idempotent.
- [x] Explicit BMTC/BMRCL HTTPS adapters with no assumed official credentials, scraping or live endpoint.
- [x] Protected stop, route, date-filtered trip patterns, transfer, feed and structural network APIs; PostGIS proximity with generated geography/GiST.
- [x] Read-only runtime grants/RLS for all thirteen new tables; existing private Auth/security rules preserved.
- [x] Synthetic GTFS-Realtime freshness boundary contract; no live worker or cancellation inference.
- [x] Windows import/refresh/rollback runbook and source register in [TRANSIT_DATA.md](../TRANSIT_DATA.md).
- [ ] Accept a reviewed BMTC feed and independently verify representative Bengaluru coverage, directions, service schedules and inter-provider transfers.

Deliverables are the transit package, additive `0002_transit_data` migration, runtime grant upgrade script, import/activate CLI, protected catalog APIs, automated tests, public aggregate evaluation evidence and updated architecture/feature/scenario/decision records. No raw feed, credential, location history or dump is committed.

## Edge cases and automated tests
Malformed or unsafe ZIP/CSV, unsupported tables/features, duplicate IDs/sequence records, nonfinite/out-of-range coordinates, missing stop/route/service references, reversed calendar/time/shape distances, date-only calendars, holidays, overnight times, overlapping frequency windows, unavailable providers, missing direction/shapes/transfers, wildcard searches, future timestamps, stage/activate/rollback, provider/mode isolation, forbidden cross-feed activation, concurrent refresh and mid-import SQL failure.

Portable tests use authored synthetic inputs, actual request validation/JWT verification and SQLite for nonspatial behavior. Real PostgreSQL tests verify migration upgrade/downgrade/no drift, PostGIS proximity and geography, RLS and SQL grants, non-owner identity isolation, concurrent refresh and transactional failures. Genuine local Supabase sign-in/JWKS and protected transit access are tested separately. Implementation run before the acceptance audit: **83 passed, zero skipped** (8 real PostgreSQL and 1 genuine Supabase integration tests included); Ruff lint/format, strict mypy and dependency checks pass. See [PHASE_STATUS.md](../PHASE_STATUS.md) for environment and warning details; skipped checks are never accepted as evidence.

## Real dataset and operational evidence (2026-10-26)
The community [BMRCL source](https://github.com/Vonter/bmrcl-gtfs/tree/f402c4c69a5d314320024f84620fa83e909c4188) was downloaded and imported into a separate disposable PostGIS database. Source revision `f402c4c69a5d314320024f84620fa83e909c4188`; ZIP SHA-256 `c19f56f32ad53525c71191125409dc8dded12dd2cebfc576ad9a4db23a62b8a7`; retrieval `2026-10-26T06:33:34Z`; service coverage `2026-08-17` through `2027-08-17`. Dataset publication time is unknown, not replaced by retrieval time.

Validated 488 stop records (includes station hierarchy, not 488 stations), 3 routes, 3,279 trips, 88,906 stop times, 4 services, 64 calendar exceptions, 19 shapes/4,541 points and 16 transfer records. Structural report: 164 directed adjacent-stop edges, one weak component, zero unserved platform records. Optional tables were explicitly not imported. These counts do not prove timely/complete operational coverage.

A genuine Supabase session and non-owner API login verified staged searches return 503, unauthenticated searches return 401, readiness/search return 200 after explicit activation, actual 100m PostGIS search returns six nearby records, three route records, date-filtered patterns and sixteen transfers. Repeat import and activation CLI both returned 0. This source was activated only in the disposable evaluation database; the development catalog was not silently populated.

Source attribution: Vonter/bmrcl-gtfs contributors, BMRCL timetable inputs and OpenStreetMap contributors (ODbL). Intermediate times are approximations and short-loop coverage is imperfect. This is real community **static** data, not agency-authorized live data. [Aggregate evidence](../evidence/phase02-community-bmrcl.json) excludes raw source rows and secrets. Download, manifest, query evidence and dump remain in ignored local storage.

A separate synthetic backup/restore preserved revision `0002_transit_data`, both stops, active dataset pointer, SRID 4326 and all 27 RLS tables; dump was 93,747 bytes. This was an executed database restore, not generated SQL.

## Completion criteria and acceptance result
| Criterion | Result |
|---|---|
| Migrations and preserved accepted backend behavior | Verified locally |
| Repeatable rights-documented import and provenance | Verified for pinned community BMRCL and authored synthetic fixtures |
| Invalid/partial imports never replace last-known-good | Verified with malformed data, SQL failure and concurrent writers |
| Spatial search, authentication and least privilege | Verified against actual PostGIS, non-owner roles and genuine Supabase Auth |
| Coverage, quality and simulation labels visible | Implemented and tested; community timing caveats retained |
| Reviewed representative BMTC import | Unresolved: source-content rights/authorization and data-quality acceptance |
| Authoritative current bus/metro/interchange coverage | Unresolved: independent provider/operational verification |
| Full Phase 02 acceptance | **Not yet met** |

## Safety gate and remaining limitations
Missing GPS is uncertainty, never confirmed cancellation. Static API service state is unknown and realtime status unavailable. GTFS-RT observations are contract tests only. Connectivity is structural per snapshot, not direction-aware timed journey feasibility or inter-provider/accessibility approval. No inferred walking links, live graph edits or automatic rerouting are enabled. Congestion-safe recovery still requires later network-impact tests. The supported fixed-route profile, manual refresh process, provisional stale threshold and lack of city-scale load certification are documented in [TRANSIT_DATA.md](../TRANSIT_DATA.md). Hosted CI and production/hosted Supabase deployment are not claimed verified.

## Main changed files
- [Transit package](../../backend/app/transit/): schema, provenance/freshness contracts, bounded validation, adapters, ingestion, owner CLI and authenticated catalog routes.
- [Migration](../../backend/migrations/versions/0002_transit_data.py), [Alembic environment](../../backend/migrations/env.py), [application factory](../../backend/app/main.py), [runtime provisioning](../../backend/sql/runtime_role.sql) and [upgrade grants](../../backend/sql/transit_runtime_grants.sql).
- [Portable transit tests](../../backend/tests/test_transit.py), [PostGIS transit tests](../../backend/tests/test_transit_postgres.py), shared disposable database fixture and existing migration/Supabase regression checks.
- Runtime/dev dependency files move HTTPX into runtime requirements; no future phase stack component added.
- [Engineering instructions](../../AGENTS.md), [source/runbook](../TRANSIT_DATA.md), architecture, decisions, feature matrix, scenarios, roadmap, phase status, database runbook, README and [aggregate source evidence](../evidence/phase02-community-bmrcl.json).

## Subsequent acceptance audit - 2026-10-26
Latest result: **87 passed, zero skipped**, including actual PostgreSQL and Supabase integration checks. The [acceptance audit](../PHASE_02_ACCEPTANCE_AUDIT.md), [rights registry](../DATA_SOURCES.md) and [coverage report](../evidence/phase02-network-coverage.json) refine the previous evidence. 488 stop records comprise 83 stations, 170 platforms and 235 entrances; all 88,906 timepoint flags are approximate. The platform graph has one weak but 151 strong components; walking/accessible transfer feasibility is not implemented or inferred. Official map/Yellow-count corroboration is partial; current authoritative schedules, complete inventory and platform-direction mapping remain unresolved. Underlying-content clearance for public use is unverified for both provider chains. A controlled synthetic fallback is proposed only for Phase 02 engineering validation. Full acceptance is not met and Phase 03 remains unstarted.
