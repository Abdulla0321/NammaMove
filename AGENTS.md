# NammaMove engineering instructions
Work in this existing repository; never initialize a nested repository or rename the project.
Read docs/MASTER_PLAN.md, docs/PHASE_STATUS.md and the relevant phase before implementation.
Preserve API compatibility and existing regression tests. Make focused changes and update phase evidence.

## Safety and truthfulness
- Missing/stale GPS means uncertainty, never confirmed cancellation without independent evidence.
- Separate feed freshness, service status, confidence and incident verification. Only trusted verified evidence may close edges in production; request flags in the simulator are not authorization.
- Rerouting must account for downstream capacity and congestion; the current penalty is illustrative only. Require network impact tests before live automatic rerouting.
- Keep simulation labels visible. No simulated feed may be described as live.
- Never commit credentials, private keys, location histories or licensed raw feeds. Use environment variables and ignored local .env files.

## Standards
Python 3.12+, FastAPI/Pydantic, typed public functions, Ruff lint/format and strict mypy for app code. Run from root:
`python -m pip install -r backend/requirements-dev.txt`
`python -m ruff check .` / `python -m ruff format --check .` / `python -m mypy` / `python -m pytest -q`.
Add behavioral tests for safety, API contracts and failure paths; avoid tests that merely mirror implementation.
Introduce dependencies only in their scheduled phase. Future clients use React Native/Expo and React with strict TypeScript, linting, formatting and component tests when introduced.
Record architecture decisions in docs/DECISIONS.md. Do not claim a planned feature is implemented. No deployment or payment integration without its phase gates.

## Database/security changes (Phase 01 onward)
Use `python -m alembic upgrade head` with a separate migration-owner DATABASE_URL; never create tables during API startup. Runtime must be a non-owner/non-BYPASSRLS login with transaction-local verified identity. Keep the nammamove schema out of Supabase exposed schemas. Private /v1 APIs must derive owner IDs from verified JWTs and authorize every access. User metadata cannot grant roles.
Run `python -m pytest -q`; real PostGIS tests require an empty disposable *_test database via NAMMAMOVE_TEST_DATABASE_URL and `python -m pytest -q -m postgres`. Never treat skipped database tests or generated SQL as proof a migration/RLS/restore succeeded. Credentials/dumps must remain ignored. See docs/DATABASE.md for Windows setup and acceptance gates.

## Transit data changes (Phase 02 onward)
Use [docs/TRANSIT_DATA.md](docs/TRANSIT_DATA.md) for provenance, licensing, supported GTFS scope and owner-run import/activation commands. Keep immutable snapshot rows and provider/mode isolation. Run genuine PostGIS tests for spatial queries, concurrency, RLS/grants and atomic rollback; a SQLite pass is not spatial evidence. Do not enable a source without reviewed rights and documented quality limitations. Never publish raw licensed feeds or claim community scheduled estimates are official/live. Phase 03 stays gated on Phase 02 acceptance.

## User-authorized Phase 03 fixture scope
The explicit Phase 03 request authorizes local development/testing with independently authored synthetic GTFS and geographic data while Phase 02 external source/coverage blockers remain open. This exception does not accept Phase 02 or authorize real Bengaluru/live deployment. Use [docs/ROUTING.md](docs/ROUTING.md) for pinned OTP builds, sealed graph provenance, rollback and actual-service tests. Retain simulation labels and disable this fixture endpoint in production. Never treat candidate ranking as guaranteed global fare optimality or congestion-safe rerouting.
