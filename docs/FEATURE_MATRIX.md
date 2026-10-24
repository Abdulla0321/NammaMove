# Feature matrix
Implemented refers to local demo behavior, not production readiness.

| Feature | Current evidence/state | Phase |
|---|---|---|
| Health/network APIs | Implemented; test_api.py | 00 |
| Directed bus/metro/walk planning | Seven sample edges; test_engine.py | 00 |
| Incident blocks/delays | Demo verification flags tested | 00; trusted lifecycle 06 |
| Missing GPS uncertainty | Engine and HTTP boundary tests | 00; live 05 |
| Capacity preference | Static penalty tested; aggregate safety absent | 00; production 06 |
| PostgreSQL/PostGIS and migrations | Planned; optional Compose only | 01 |
| Supabase Auth and authorization | Planned | 01 |
| Bengaluru GTFS and provenance | Planned | 02 |
| OTP schedule/accessibility routing | Planned | 03 |
| Expo mobile and React shell | Planned | 04 |
| Offline/manual origin, favorites, languages | Planned | 04 |
| Live tracking and notifications | Planned | 05 |
| Trusted reports, recovery, congestion control | Planned | 06 |
| Predictive reliability/ETA ranges | Planned | 07 |
| Authorized ticketing/payments/refunds | Planned | 08 |
| Operations, replay and resilience | Planned | 09 |
| Deployment and approved pilot | Planned | 10 |
| Lint/format/type/test and CI configuration | Local checks recorded in PHASE_STATUS | 00 |
