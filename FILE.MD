# NammaMove — Implemented Features Inventory (Code-Proven)

_Last analyzed: 2026-11-11 from this repository state._

This document summarizes **what is implemented now**, with proof pointers to code and test/docs evidence.  
It also explicitly marks what is **not implemented yet** to avoid confusion during main-branch review.

---

## 1) Current Project Scope

NammaMove is currently a **phase-based mobility platform** with:

- A FastAPI backend (`backend/app`) for simulation, secured APIs, static transit catalog APIs, and synthetic OTP routing.
- A React Native + Expo mobile client (`apps/mobile`) plus web preview shell.
- Dockerized local infrastructure (PostGIS + OTP compose files).
- Strong local test and CI pipelines.

Primary status source: `docs/PHASE_STATUS.md` and `docs/FEATURE_MATRIX.md`.

---

## 2) Implemented Features by Area

## A. Core Simulation API (Implemented)

### Implemented
- `GET /health` simulation health endpoint.
- `GET /network` returns sample stops/edges in simulation mode.
- `POST /journeys/plan` deterministic sample routing with incident inputs.
- `GET /services/status` separates service status vs feed status; does not infer cancellation from missing GPS.

### Proof
- `backend/app/simulator.py`
- Tests: `backend/tests/test_api.py`, `backend/tests/test_engine.py`

---

## B. Backend Security + Identity (Implemented)

### Implemented
- Bearer token auth for protected routes.
- Supabase JWT verification with JWKS (`RS256`/`ES256`), issuer/audience/required claims checks.
- App role mapping (`commuter`, `moderator`, `admin`) from trusted metadata.
- Rejects anonymous/invalid role tokens.
- Role-gated dependencies for moderator/admin endpoints.

### Proof
- `backend/app/auth.py`
- `backend/tests/test_security.py`
- Integration: `backend/tests/test_supabase_integration.py`

---

## C. Persistent Phase-01 APIs (Implemented)

All under `/v1` and auth-protected.

### Implemented
- Profile lifecycle:
  - `PUT /v1/me`, `GET /v1/me`, `DELETE /v1/me`
- User preferences:
  - `PUT /v1/me/preferences`
- Admin catalog writes:
  - `POST /v1/operators`, `POST /v1/stops`
- Stop listing:
  - `GET /v1/stops`
- Journey history:
  - `POST /v1/journeys`, `GET /v1/journeys`, `GET /v1/journeys/{id}`, `DELETE /v1/journeys/{id}`
- Disruption reporting and verification:
  - `POST /v1/disruptions`, `GET /v1/disruptions/{id}`, `POST /v1/disruptions/{id}/verification`
- Notifications:
  - `GET /v1/notifications`, `POST /v1/notifications/{id}/read`

### Proof
- `backend/app/api.py`
- Data models: `backend/app/models.py`
- Persistence tests: `backend/tests/test_persistence.py`

---

## D. Database + PostGIS + Migration Stack (Implemented)

### Implemented
- SQLAlchemy schema for commuters, operators, stops, routes, trips, stop times, disruptions, vehicles, journeys, notifications, audit events.
- Transit snapshot/GTFS tables for dataset versioning and read APIs.
- Alembic migrations with readiness checks for expected revision + PostGIS extension.
- Runtime DB connectivity abstraction and per-request session dependency.
- Retention CLI (`maintenance.py`) with dry-run default and owner-only apply safeguards.

### Proof
- `backend/app/models.py`
- `backend/app/transit/models.py`
- `backend/app/main.py` (`/health/ready`)
- `backend/app/database.py`
- `backend/app/maintenance.py`
- Tests: `backend/tests/test_migrations.py`, `backend/tests/test_persistence.py`, `backend/tests/test_transit_postgres.py`

---

## E. Transit Dataset Ingestion + Catalog APIs (Implemented)

### Implemented
- Owner-controlled GTFS ingest flow:
  - checksum/digest idempotency
  - validation + quarantine behavior
  - activation/rollback support
  - provider-mode checks (BMTC/BMRCL/synthetic route-type constraints)
- Auth-protected static catalog APIs under `/v1/transit`:
  - `GET /feeds`
  - `GET /stops` (includes optional PostGIS radius search)
  - `GET /routes`
  - `GET /network`
  - `GET /patterns` (service-date filtering + timepoint metadata)
  - `GET /transfers`

### Proof
- `backend/app/transit/ingestion.py`
- `backend/app/transit/routes.py`
- Contracts/validation: `backend/app/transit/contracts.py`, `backend/app/transit/validation.py`
- Tests: `backend/tests/test_transit.py`, `backend/tests/test_transit_postgres.py`

---

## F. Synthetic OTP Routing (Phase 03, Implemented)

### Implemented
- Protected endpoint:
  - `POST /v1/routing/plan`
- OTP provider adapter with bounded behavior:
  - strict query/response validation
  - response size/time budgets
  - bounded concurrency (`BoundedSemaphore(4)`)
  - strict itinerary normalization and chronology checks
  - wheelchair/transfers/walk limits
  - preference ranking (`fastest`, `cheapest`, `fewest_transfers`, `least_walking`)
- Graph release verification + manifest-based versioning.
- Routing contract metadata includes explicit synthetic confidence and safety limits.

### Proof
- `backend/app/routing/routes.py`
- `backend/app/routing/provider.py`
- `backend/app/routing/contracts.py`
- Build/release tooling: `backend/app/routing/build.py`, `backend/app/routing/fixture.py`
- Tests: `backend/tests/test_routing.py`, `backend/tests/test_routing_otp.py`, `backend/tests/test_routing_genuine.py`

---

## G. Realtime Foundation (Phase 05 slice, Implemented as internal primitives)

### Implemented
- Synthetic fixture replay model and validation.
- Bounded GTFS-RT protobuf normalization adapter (subset only, full-dataset envelope behavior constrained).
- Atomic Redis state primitive with:
  - WATCH/MULTI/EXEC write pattern
  - dedup/order guards
  - bounded retries/capacity
  - TTL-bounded observation records
  - fail-closed behavior on corruption/outage

### Important scope note
- These are **internal primitives/foundation**, not a complete production live-tracking pipeline.

### Proof
- `backend/app/realtime/replay.py`
- `backend/app/realtime/gtfs_rt.py`
- `backend/app/realtime/redis_state.py`
- Tests: `backend/tests/test_realtime_replay.py`, `backend/tests/test_realtime_gtfs_rt.py`, `backend/tests/test_realtime_redis.py`
- Status evidence: `docs/PHASE_STATUS.md` (Phase 05 sections)

---

## H. API App Hardening / Observability (Implemented)

### Implemented
- Global request middleware:
  - request IDs
  - body-size cap (64 KiB)
  - security headers (`x-content-type-options`, `cache-control: no-store`)
  - structured JSON logs without leaking payloads/secrets
- Sanitized DB and validation exception handlers.
- Config validators for URL/env safety and production requirements.
- Optional strict CORS origin list from settings.

### Proof
- `backend/app/observability.py`
- `backend/app/main.py`
- `backend/app/config.py`
- Tests: `backend/tests/test_client_cors.py`, `backend/tests/test_api.py`

---

## I. Mobile App + Web Preview (Implemented)

### Implemented
- Expo React Native app scaffolding with strict TypeScript.
- Auth flows via Supabase:
  - sign in
  - sign up (with confirmation handling path)
  - session subscription
  - sign out local scope
- Routing request client to backend with:
  - auth token injection
  - one refresh retry on 401
  - timeout + response size safety bound
  - schema validation of responses
- Journey planning UI with preferences and mode options.
- Saved library model:
  - favorites
  - recent searches
  - cached journeys
  - bounded limits and cache expiry checks
- Localization structure for `en`, `kn`, `hi` with fallback.
- Native secure storage strategy (chunked secure-store adapter) and memory-only web storage.
- Optional native map enablement logic and fallback behavior.

### Proof
- Entry/UI: `apps/mobile/App.tsx`
- Service/auth layer: `apps/mobile/src/services.ts`
- API client: `apps/mobile/src/api.ts`
- Library/cache: `apps/mobile/src/library.ts`
- i18n: `apps/mobile/src/i18n.ts`
- Map runtime: `apps/mobile/src/mapRuntime.ts`
- Tests: `apps/mobile/__tests__/*`
- Manual runbook/evidence: `docs/MOBILE.md`, `docs/PHASE_STATUS.md`

---

## J. DevOps / Tooling / Quality Gates (Implemented)

### Implemented
- Docker assets:
  - `compose.yaml` (PostGIS)
  - `compose.routing.yaml` (OTP routing service)
  - `backend/Dockerfile`
- Python quality gates configured:
  - Ruff lint/format
  - strict mypy
  - pytest markers for postgres/otp/supabase/redis
- GitHub Actions CI jobs for:
  - mobile checks
  - backend checks (Ubuntu + Windows, py3.12/3.14)
  - PostGIS integration
  - OTP synthetic build/test

### Proof
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `compose.yaml`, `compose.routing.yaml`, `backend/Dockerfile`

---

## 3) Features Explicitly NOT Implemented / Not Accepted Yet

These are intentionally out-of-scope or not fully accepted yet per project docs:

- Live production transit tracking pipeline (full operational feed workers, delivery APIs, durable production ingestion).
- Trusted city-wide disruption recovery and congestion-safe rerouting (future Phase 06).
- Predictive ML reliability/ETA ranges (future Phase 07).
- Ticketing/payments/refunds (future Phase 08).
- Production operations/replay/SLO and approved deployment pilot (Phases 09–10).
- Full real-data rights/coverage closure for Bengaluru feeds remains documented as an external gate.

Proof references:
- `docs/FEATURE_MATRIX.md`
- `docs/PHASE_STATUS.md`
- `docs/TRANSIT_DATA.md`
- `docs/REALTIME.md`

---

## 4) Quick "Implemented Endpoints" Index

### Public/simulation
- `GET /health`
- `GET /network`
- `POST /journeys/plan`
- `GET /services/status`
- `GET /health/ready`

### Auth-protected
- `/v1/*` persistence APIs (`backend/app/api.py`)
- `/v1/transit/*` catalog APIs (`backend/app/transit/routes.py`)
- `/v1/routing/plan` synthetic OTP routing (`backend/app/routing/routes.py`)

---

## 5) Primary Evidence Files to Review

- `README.md`
- `docs/FEATURE_MATRIX.md`
- `docs/PHASE_STATUS.md`
- `docs/DATABASE.md`
- `docs/ROUTING.md`
- `docs/MOBILE.md`
- `docs/REALTIME.md`

---

## 6) Bottom Line

This repository already implements:

1. A secured backend with persistence and PostGIS-backed transit catalog APIs.
2. A synthetic-but-real OTP integration path for authenticated routing.
3. A production-minded mobile client shell with auth, planning, cache, and localization.
4. A tested Phase-05 realtime foundation (adapter + Redis state primitives), not yet a full live ops pipeline.

So: **substantial implementation exists across Phases 00–05 foundations**, while real-world live-data/operations/deployment phases remain intentionally unfinished and documented as such.
