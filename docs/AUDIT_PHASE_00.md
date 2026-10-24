# Phase 00 repository audit ? 2026-10-25
All original tracked files were inspected; original tree:
```
nammamove-starter/
  README.md, .env.example, .gitignore, compose.yaml
  backend/Dockerfile, requirements.txt
  backend/app/__init__.py, engine.py, main.py
  backend/tests/test_engine.py
  docs/ARCHITECTURE.md, PRODUCT_ROADMAP.md
```
The wrapper had no independent package or repository purpose. Its contents were moved to the existing Git root; Git history is retained and no repository was initialized.

## Existing functionality
FastAPI exposes GET /health, GET /network, POST /journeys/plan, GET /services/status. Pydantic validates route and incident bodies. A heap-based directed shortest-path engine uses seven illustrative bus/metro/walk edges, verified incident delays/blocks, uncertainty and capacity penalties. Seven original tests cover baseline routes, verified blocks/delays, unverified reports, GPS uncertainty, direction and capacity preference.
Runtime dependencies: FastAPI, Uvicorn standard extras, Pydantic. Pytest and HTTPX moved to development requirements; Ruff and mypy added. Dockerfile serves API; Compose defines optional PostGIS and Redis, unused by API. No Replit configuration, dependency, runtime hook or host assumption was found. No real credential was found in original tracked files; localdev was a sample Compose password and has been replaced with required local environment configuration.

## Gaps and architectural limits
No mobile/admin client, persistence, migration, authentication, licensed GTFS/GTFS-RT, OTP, live tracking, worker, payment, ML, deployment or production observability exists. Simulation accepts a client-provided verified flag and operator_cancelled boolean: suitable only for a local demo, unsafe as production authority. Confidence, provenance, expiry, duplicate reports and moderation are absent. Capacity is a static soft penalty; simultaneous reroutes can still overload alternatives. Estimated minutes include risk penalties, not a calibrated ETA. There is no schedule/transfer feasibility, accessibility, timezone/calendar, geospatial matching or network assignment. Same-origin queries produce an empty itinerary even for unknown stops (existing behavior). Engine assumes nonnegative trusted edge costs. No rate limits, request-size budgets or production incident trust boundary exist.

## Foundation remediation
Root layout, documented Windows setup, isolated dependencies, lint/format/type gates, API regression tests, negative telemetry-age validation, environment sample, credential ignores and least-privilege CI are introduced. Existing route selection remains intact. Remaining gaps are explicitly assigned to later phases, not silently represented as working features. Dependency bounds are not a reproducible lockfile; adopt reviewed locks and vulnerability scanning before deployment.
