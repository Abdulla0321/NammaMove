# NammaMove
Bengaluru-first disruption-aware mobility platform. Phase 01 adds persistent FastAPI APIs and Supabase JWT authorization alongside the illustrative routing simulator. No live transit integration or frontend exists yet.

## Windows PowerShell quickstart
Run from the existing repository root:
```powershell
cd "C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --no-access-log
```
Use Python 3.12 or newer. Activation is optional; these commands work when PowerShell blocks activation. Open http://127.0.0.1:8000/docs or GET /health. Ctrl+C stops the API. No database, account or .env is required for the simulator.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest -q
```
To format intentionally: ` .\.venv\Scripts\python.exe -m ruff format .`.

## API example
POST /journeys/plan:
```json
{"origin":"Electronic City","destination":"MG Road","incidents":[{"id":"closure-demo","affected_edges":["bus-2"],"kind":"road_closure","verified":true,"blocked":true}]}
```
GET /network lists the sample stops. GET /services/status distinguishes service status from feed status. Missing GPS never confirms cancellation. Request verification and cancellation flags are **simulation inputs**, not production authorization. Capacity penalties are illustrative and cannot guarantee safe network-wide rerouting.

## Database and security setup
See [docs/DATABASE.md](docs/DATABASE.md) for PostgreSQL/PostGIS startup, Alembic migrations, separate runtime credentials, Supabase signing keys, protected `/v1` APIs, RLS, privacy retention and integration tests. `/health` remains simulator liveness; `/health/ready` verifies persistence readiness. Without database/Auth configuration, simulator routes still work and persistent endpoints fail closed.

## Optional Docker tools
Build API: `docker build -t nammamove-api backend`; run: `docker run --rm -p 127.0.0.1:8000:8000 nammamove-api`.
For database setup, copy `.env.example` to ignored `.env`, replace POSTGRES_PASSWORD locally, then run `docker compose up -d`. Stop with `docker compose down` (preserves the database volume). Persistent `/v1` APIs use DATABASE_URL; the simulator does not connect to these services. Redis is deferred under the future-cache profile. Never commit .env or real credentials; production secrets belong in a secret manager. The API reads root `.env`; use a non-owner runtime login as described in the database runbook.

## Layout and roadmap
- backend/app: API and deterministic routing engine
- backend/tests: routing, disruption and HTTP contracts
- docs/MASTER_PLAN.md: authoritative eleven-phase roadmap
- docs/PHASE_STATUS.md: completion evidence and remaining gates
- docs/AUDIT_PHASE_00.md: full original inventory and known limitations
- docs/phases: prerequisites, tasks, tests and acceptance criteria
- .github/workflows/ci.yml: Windows/Linux quality gates

React Native + Expo, React/TypeScript, PostgreSQL/PostGIS, Supabase Auth, OpenTripPlanner, GTFS/GTFS-Realtime, Redis and Python ML are introduced progressively; PostgreSQL/PostGIS and Supabase verification now have Phase 01 implementations. No original Namma-Yatra source was copied; preserve provenance and third-party licenses when adding assets or feeds.

## Static Bengaluru transit catalog (Phase 02)
Versioned GTFS import/rollback and protected stop/route/PostGIS searches are implemented separately from simulator routing. See [transit data runbook and source rights](docs/TRANSIT_DATA.md) and [Phase 02 acceptance report](docs/phases/PHASE_02.md). A real community BMRCL snapshot passed isolated import/search checks; timings include upstream estimates. Official/live feeds and complete BMTC/Bengaluru coverage remain unresolved. Phase 03 is not started.

## Synthetic schedule routing (Phase 03)
An opt-in authenticated OTP adapter now plans over independently authored bus/metro/street fixtures with calendar, direction, transfer, wheelchair and walking constraints. Graph builds and responses remain explicitly simulated. See [Windows routing setup](docs/ROUTING.md), [Phase 03 acceptance scope](docs/phases/PHASE_03.md) and [evidence](docs/evidence/phase03-routing.json). External Bengaluru data rights/coverage remain blocked; no live routing or Phase 04 client is enabled.
