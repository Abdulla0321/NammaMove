# NammaMove architecture
## Current implementation
FastAPI calls a pure in-memory shortest-path engine over seven directed illustrative edges. Pydantic validates requests. API: GET /health, GET /network, POST /journeys/plan, GET /services/status. Uncertainty and capacity penalties modify generalized duration. Phase 01 adds SQLAlchemy persistence in a private PostgreSQL/PostGIS schema and Supabase asymmetric JWT verification for versioned /v1 APIs. No frontend or live feed exists. Request-supplied verified/operator_cancelled flags are local simulation controls, not production authorization.

## Target architecture
Expo/React Native rider app and React/TypeScript operations console call a FastAPI modular monolith. Supabase Auth supplies identity; server validates tokens and roles. PostgreSQL/PostGIS stores durable catalog, evidence, journeys and audit data. Import workers validate licensed GTFS and atomically promote versioned snapshots. OpenTripPlanner builds and serves schedule-aware GTFS/OSM graphs. GTFS-RT workers separate feed freshness from service state. Redis provides ephemeral cache/queues, never sole financial or evidence storage. Recovery enforces feasibility and network impact constraints. Python ML workers train scikit-learn/XGBoost reliability models; inference returns calibrated uncertainty. Authorized provider adapters handle payments and tickets.

Data flow: authorized source -> validation/quarantine -> snapshot/evidence store -> OTP/incident overlay -> journey/recovery API -> clients. Replay simulation and observability measure network outcomes; accepted journey demand updates load estimates.

## Domain boundaries and data
Modules: catalog/calendar, feed quality, routing, evidence/moderation, active journeys/recovery, identity/preferences, notifications, prediction, tickets/ledger and operations. Add modules before splitting services. Planned entities: operators, stops, routes, trips, stop_times, shapes, feed_snapshots, vehicle_positions, service_alerts, incidents, incident_evidence, graph_overrides, journey_plans, active_journeys, user_preferences, notifications, tickets, payments and audit_events.

## Safety semantics
Freshness (live/stale/unavailable/simulation) and operational state (scheduled/delayed/uncertain/confirmed_cancelled) are independent. Missing GPS reduces confidence but cannot confirm cancellation. Closures require authorized evidence, provenance, observed/expiry timestamps and an audit trail. Unverified reports may annotate risk, never automatically remove edges.

Feasibility precedes ranking: direction, calendar, transfer time, accessibility and reachable alighting. Physical ETA must be separate from ranking penalties. Estimate aggregate load from concurrent recommendations; reject/throttle harmful diversions, apply minimum-benefit cooldown and preserve rider confirmation. Absent capacity evidence or a safe alternative, explain uncertainty and waiting/support options. The current static penalty cannot guarantee congestion-safe recovery.

## Security and deployment
Authenticate ingestion and privileged actions; scope subscriptions; validate all external inputs; limit requests and worker budgets. Keep Supabase service secrets server-side. Minimize location retention and redact logs. Verify provider webhooks and use transactional idempotency. Independently version graphs, models and schema; maintain rollback compatibility. Docker/CI start locally; production requires Phase 10. No Kubernetes dependency is required.

## Tooling references
[Ruff configuration](https://docs.astral.sh/ruff/configuration/), [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/). Validate future integration versions and licenses when their phases begin.

## Phase 01 implementation boundary
Application factory assembles separate simulator and persistent routers. Modules: config (validated environment), database (bounded pool and transaction-scoped sessions), models (14 domain tables), auth (Supabase JWKS and role dependencies), schemas (strict request/response contracts), api (owned records and privileged writes), observability (bounded bodies and private JSON request events), maintenance (explicit owner-only retention). Frozen Alembic revision creates the schema, generated geography/GiST index and RLS policies. Runtime provisioning grants exclude evidence/audit mutation. See DATABASE.md for operational setup and validation limits.

Profile, preferences, sample journey history, manually maintained catalog and notifications are persistent. Disruption reporting/moderation is a security primitive with evidence and audit, not a live recovery system. Vehicles require a cancellation-evidence reference independently of feed status; future ingestion must validate authority and lifetime. Persistent reports never alter Phase 00 routing. Full incident lifecycle, data ingestion, OTP, live tracking and aggregate congestion enforcement remain in their existing future phases.
