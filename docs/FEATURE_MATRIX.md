# Feature matrix
Implemented refers to local demo behavior, not production readiness.

| Feature | Current evidence/state | Phase |
|---|---|---|
| Health/network APIs | Implemented; test_api.py | 00 |
| Directed bus/metro/walk planning | Seven sample edges; test_engine.py | 00 |
| Incident blocks/delays | Demo verification flags tested | 00; trusted lifecycle 06 |
| Missing GPS uncertainty | Engine and HTTP boundary tests | 00; live 05 |
| Capacity preference | Static penalty tested; aggregate safety absent | 00; production 06 |
| PostgreSQL/PostGIS and migrations | Implemented; real local migrations, spatial constraints, RLS/grants and restore passed | 01 |
| Supabase Auth and authorization | Genuine local official Supabase Auth ES256/JWKS, roles and non-owner ownership tests passed | 01 |
| GTFS schema, validation, versions and rollback | Implemented; synthetic and real PostGIS tests; provider access/coverage gates remain | 02 |
| Protected stop/route/spatial/pattern/transfer APIs | Implemented; real PostGIS distance and read-only RLS/grants tested | 02 |
| BMTC import entitlement | Not established; detailed source/rights registry, no BMTC feed downloaded/imported | 02 |
| Official complete BMTC/BMRCL datasets | Partial topology corroboration; current schedules, exhaustive inventory and public-use content rights unresolved | 02 |
| Read-only coverage and network audit | Real snapshot: 83 stations, 170 platforms, 235 entrances; strong/weak connectivity distinguished | 02 |
| Approximate timetable labels | Source timepoint and timing_precision exposed; agency_schedule_accuracy_verified=false | 02 |
| GTFS-RT freshness contract | Synthetic boundary tests; no live ingestion worker | 02/05 |
| OTP schedule/street/accessibility routing | Implemented on owned synthetic graph; actual OTP calendar/direction/transfer/wheelchair tests | 03 |
| Departure/arrival-time and journey preferences | Implemented over bounded candidates; no global optimum or real agency schedule claim | 03 |
| Graph build/versioning/rollback | Pinned image/platform, canonical inputs, source/graph hashes, real build/load and explicit rollback verified | 03 |
| Routing faults and bounded-load target | Real outage/recovery plus four-concurrent-request authenticated fixture benchmark; production/city-load gates open | 03 |
| Expo mobile and React shell | Planned | 04 |
| Offline/manual origin, favorites, languages | Planned | 04 |
| Live tracking and notifications | Planned | 05 |
| Trusted reports, recovery, congestion control | Planned | 06 |
| Predictive reliability/ETA ranges | Planned | 07 |
| Authorized ticketing/payments/refunds | Planned | 08 |
| Operations, replay and resilience | Planned | 09 |
| Deployment and approved pilot | Planned | 10 |
| Lint/format/type/test and CI configuration | Local checks recorded in PHASE_STATUS | 00 |

Phase 01 also implements private-schema RLS/grant definitions, commuter preferences, owned journey history and notifications, basic report evidence/audit, JSON logs, readiness, deletion/redaction and explicit retention. See PHASE_STATUS.md for measured local evidence and external gates. These persistence/security primitives do not change the planned live recovery or operations phases.

Latest [Phase 02 acceptance audit](PHASE_02_ACCEPTANCE_AUDIT.md): **87 tests passed, zero skipped**. [Source registry](DATA_SOURCES.md) and [coverage JSON](evidence/phase02-network-coverage.json) record evidence and gaps. Synthetic fallback is limited to pipeline validation and does not satisfy real-provider acceptance.

Phase 03 is user-authorized synthetic development only; [local acceptance scope](phases/PHASE_03.md) and [routing runbook](ROUTING.md) preserve all Phase 02 source/coverage blockers. Phase 04 is unstarted.
