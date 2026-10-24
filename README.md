# NammaMove
Bengaluru-first disruption-aware mobility platform. Currently a **simulation-only FastAPI backend** with an illustrative directed network; no live transit service or frontend exists yet.

## Windows PowerShell quickstart
Run from the existing repository root:
```powershell
cd "C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1
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

## Optional Docker tools
Build API: `docker build -t nammamove-api backend`; run: `docker run --rm -p 127.0.0.1:8000:8000 nammamove-api`.
For future database/cache work, copy `.env.example` to ignored `.env`, replace POSTGRES_PASSWORD locally, then run `docker compose up -d`. Stop with `docker compose down` (preserves the database volume). The simulator does not connect to these services. Never commit .env or real credentials; production secrets belong in a secret manager. APP_ENV and future URL examples are reserved configuration, not connected integrations.

## Layout and roadmap
- backend/app: API and deterministic routing engine
- backend/tests: routing, disruption and HTTP contracts
- docs/MASTER_PLAN.md: authoritative eleven-phase roadmap
- docs/PHASE_STATUS.md: completion evidence and remaining gates
- docs/AUDIT_PHASE_00.md: full original inventory and known limitations
- docs/phases: prerequisites, tasks, tests and acceptance criteria
- .github/workflows/ci.yml: Windows/Linux quality gates

React Native + Expo, React/TypeScript, PostgreSQL/PostGIS, Supabase Auth, OpenTripPlanner, GTFS/GTFS-Realtime, Redis and Python ML are introduced progressively. No original Namma-Yatra source was copied; preserve provenance and third-party licenses when adding assets or feeds.
