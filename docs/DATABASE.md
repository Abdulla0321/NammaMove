# Phase 01 database and Windows runbook
See [PHASE_01_ACCEPTANCE_WINDOWS.md](PHASE_01_ACCEPTANCE_WINDOWS.md) for the resolved Docker Desktop setup history and the exact real-service acceptance/replay sequence, including safe PowerShell backup/restore commands.

## Scope and prerequisites
PostgreSQL 16 + PostGIS 3.4, SQLAlchemy 2 and Alembic provide persistence. Install Docker Desktop with a supported Linux-container backend, or install PostgreSQL/PostGIS separately. Docker Desktop and the real PostgreSQL/PostGIS service are now running; see PHASE_STATUS.md for the successful 45-test acceptance evidence. Do not confuse SQLite test doubles with PostGIS validation.

Run all commands from the existing NammaMove root. Python dependencies:
```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```
Edit ignored `.env`: replace POSTGRES_PASSWORD; set DATABASE_URL with a migration-owner identity. The driver prefix must be `postgresql+psycopg://`. URL-encode reserved characters in passwords. Do not paste real URLs/passwords into tracked files or shared shell transcripts. Environment variables override `.env`. Config errors hide input values.

```powershell
docker compose up -d postgres
docker compose ps
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```
Docker's initialization credentials apply only to a new volume; changing `.env` does not rotate an existing database password. Never delete a persistent volume to fix authentication. Redis remains optional under `--profile future-cache` and is not connected in Phase 01.

Migrations explicitly create private schema `nammamove`, install PostGIS in `public`, create the schema and enable RLS. On a managed database, an administrator may need to preinstall PostGIS in public first. Startup does not create tables or run migrations. Do not apply migrations as the API runtime login. For a disposable development DB only, `python -m alembic downgrade base` removes application tables/data; the private schema, version table and shared PostGIS extension remain. Do not use downgrade as production rollback without a reviewed backup/compatibility plan.

## Separate runtime identity
The Docker POSTGRES_USER is an administrator/bootstrap identity, not the API login. After migrations, run the reviewed grant script as administrator:
```powershell
Get-Content backend/sql/runtime_role.sql -Raw | docker compose exec -T postgres psql -U nammamove -d nammamove -v ON_ERROR_STOP=1
```
The script creates a non-login `nammamove_api` group. It is a one-time provisioning script, not an idempotent migration. In an interactive administrator psql session, create a dedicated LOGIN role without SUPERUSER, CREATEDB, CREATEROLE or BYPASSRLS; use `\password your_runtime_login` to set its password interactively, then `GRANT nammamove_api TO your_runtime_login`. Do not grant schema ownership or membership in the migration-owner role. Change local DATABASE_URL to that runtime login before starting the API. For later migrations, supply the separate migration-owner URL through the local process environment, then restore the runtime configuration.

The runtime group has CRUD table privileges, read-only migration-version access and insert/read-only evidence/audit access. Review grants for every later migration. No direct client access is supported: `nammamove` must stay outside Supabase exposed schemas; never grant schema/table access to `anon` or `authenticated`. The API's non-owner connection sets verified user ID/role using transaction-local `set_config`. RLS enforces ownership on private tables and privileged catalog writes; API checks additionally enforce roles, immutable identity and independent report verification. RLS relies on the API as trusted identity setter, not on client-supplied SQL/session settings. Schema owners/superusers bypass RLS, so do not deploy with bootstrap credentials.

## Schema
| Domain | Tables / important constraints |
|---|---|
| Commuters | commuters (Supabase UUID; no password/email copy), user_preferences; locale/walk bounds |
| Transit network | operators, stops, transit_routes, trips, stop_times; scoped external IDs, FKs, nonnegative ordered times |
| Spatial stops | bounded latitude/longitude; generated geography(Point,4326), GiST index; location is managed explicitly by migration |
| Provenance | feed_snapshots with checksum/license/source and simulation/live mode; schema only, no import |
| Vehicles | vehicles with capacity, independent feed/service states, optional last observation time; cancellation requires evidence FK |
| Disruptions | disruptions, disruption_evidence; bounded confidence, verification and expiry metadata |
| Journeys | journeys, owner FK and itinerary snapshot; currently simulation-only |
| Notifications | notifications, owner FK and idempotent read timestamp; no delivery worker yet |
| Audit | audit_events; actor IDs anonymized on local profile deletion; no request bodies/tokens |

UUIDs are generated by the application except commuter IDs, which come from verified token subjects. All timestamps represent UTC. PostgreSQL uses timestamptz. SQLite fixtures normalize timestamps for comparisons and cannot validate spatial, PostgreSQL RLS or transactional DDL semantics. Geography is a stored generated column, not a second manually mutable location. ORM autogeneration excludes this migration-managed column. Calendars/import/OTP/live telemetry remain later phases.

## Authenticated startup
Set SUPABASE_URL to the project's HTTPS origin and audience to `authenticated`. Use asymmetric Supabase signing keys (ES256 or RS256). No Supabase service-role key, JWT shared secret, password or client API key is needed by this API verifier.
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --no-access-log
```
The API loads root `.env`. `--no-access-log` prevents Uvicorn's default raw URL/query logging; NammaMove emits JSON events with server-generated request ID, method, route template, status and duration. Logs exclude token/body/query/location/profile data and raw exception strings. Apply equivalent access-log redaction at the proxy before deployment. Use `/docs` Authorize with a genuine Supabase user access token; do not commit it or a saved browser session.

Clients sign in/refresh/sign out with Supabase Auth. No local password or token minting endpoint is added. Set trusted roles only via server-managed `app_metadata.nammamove_role`: commuter (default), moderator or admin. Never use `user_metadata` for permissions. Supabase's signed top-level role must be `authenticated`; anonymous/service-role API tokens are rejected. Role changes take effect when a refreshed access token is issued; revocation/deleted Auth identities are not checked online on every request. Use short access-token lifetimes and refresh/revoke operational procedures. JWKS cache TTL is 60 seconds, no permanent per-key cache; provider refresh errors fail closed with 503. Upstream unknown-key refresh cooldown may delay newly rotated keys briefly. Configure signing keys before using protected routes; legacy HS256 secrets are intentionally unsupported.

## API contracts
| Route | Authorization / behavior |
|---|---|
| GET /health | Unchanged Phase 00 liveness `{status:ok, mode:simulation}`; not proof of DB availability |
| GET /health/ready | 200 only with configured Auth origin, expected migration revision and PostGIS; otherwise generic 503 |
| Phase 00 /network, /journeys/plan, /services/status | Explicit simulator; default enabled in development and disabled in production; flags never alter persistent records |
| PUT/GET/DELETE /v1/me | Own profile only; server derives ID from validated JWT |
| PUT /v1/me/preferences | Own bounded accessibility/walking preferences |
| POST /v1/operators, /v1/stops | Admin, existing profile; bounded names/coordinates; audited |
| GET /v1/stops | Authenticated, paginated and explicit simulation/live filter |
| POST/GET /v1/journeys | Own saved journeys; planning currently uses sample graph only |
| GET/DELETE /v1/journeys/{id} | Own only; foreign IDs return 404 |
| POST /v1/disruptions | Authenticated profile; unverified report with confidence zero; client verification fields rejected |
| GET /v1/disruptions/{id} | Reporter or moderator/admin |
| POST /v1/disruptions/{id}/verification | Independent moderator/admin; evidence source, bounded confidence, aware future expiry <=7 days; evidence and audit in same transaction |
| GET /v1/notifications, POST /v1/notifications/{id}/read | Owner only; bounded list and idempotent read |

Persistent endpoints require a valid bearer token and configured database; absence fails closed. Writes flush and commit before HTTP success; errors roll back. Return 401 for invalid/missing token, 403 for missing role/self-verification, 404 for unavailable/foreign resource, 409 for constraint conflicts, 413 for >64KiB request bodies, 422 for validation and 503 for unconfigured/unavailable dependency. Validation errors never echo input values. Readiness does not call the Auth provider on every probe. No public incident report, GPS status flag or persistent verification affects a routing graph in Phase 01. A vehicle evidence FK alone does not establish trust in future ingestion: Phase 05/06 must verify source authority and expiry before accepting cancellation or graph changes.

## Privacy and maintenance
Local profile deletion cascades preferences, journey history and notifications; incident reporter/audit actor references become null, and the departed reporter's free text is redacted. This endpoint does not delete the Supabase Auth account, revoke issued tokens or prevent profile re-creation by a still-valid external account. Coordinate full account deletion/revocation with Supabase administration before a real pilot. Evidence-source fields are operator/document references only: do not insert personal names, phone numbers or raw GPS traces.

Provisional development retention: journeys/notifications 30 days, audit events 90 days, inactive/expired disruptions and associated evidence 90 days. Evidence still referenced by a cancellation is preserved. Raw GPS histories are not collected. These windows require product/privacy approval before production and are not scheduled automatically. With a separate maintenance-owner DATABASE_URL, inspect counts first:
```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python.exe -m app.maintenance
# After reviewing counts and the target database:
.\.venv\Scripts\python.exe -m app.maintenance --apply
```
`--apply` commits deletions transactionally. Backups may retain deleted data until their approved expiry; include them in deletion/retention policy. The runtime login intentionally cannot run owner maintenance.

## Tests and restore drill
```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
```
Portable tests use in-memory SQLite plus generated signing keys and mocked JWKS transport; the separate PostgreSQL and Supabase acceptance tests use actual services. Real tests are opt-in: create a **new empty disposable database ending `_test`**, set NAMMAMOVE_TEST_DATABASE_URL locally with an administrator test identity, and run `python -m pytest -q -m postgres`. The test fixture refuses pre-existing application schemas and non-test database names; it creates/downgrades/removes only its test schema. Never use an application database. Tests verify spatial functions/index, constraints, migration roundtrip/rollback, RLS ownership/context clearing and persistent HTTP behavior. CI also runs a disposable PostGIS service and a backup/restore drill. Neither is a claim that hosted CI has run for these local changes.

For operator-controlled backups, use `pg_dump -Fc` with credentials from a local password file/secret manager, then restore into a new isolated database with `pg_restore --exit-on-error --no-owner`; preinstall PostGIS in public, recreate reviewed runtime grants and verify migration revision plus synthetic/user-count invariants. Never commit dumps; `.gitignore` excludes them. A restore success must be recorded with date, source backup, target and integrity checks. CI's synthetic restore drill is not a substitute for a production recovery exercise.

## Acceptance and release follow-up
Real PostgreSQL migrations/RLS/grants, backup/restore and genuine local Supabase Auth with a separate runtime login all passed. Hosted/full-platform interoperability remains outside this local component validation. Before production, approve privacy windows and full external account deletion; add production rate limiting, migration locking/backup policy and managed secrets before deployment. Phase 02 static import/search is now implemented; see [TRANSIT_DATA.md](TRANSIT_DATA.md) for its source rights, refresh and acceptance gates.


## Phase 02 schema/runtime upgrade
The current migration head is `0002_transit_data`; readiness expects that revision. Apply `python -m alembic upgrade head` with the owner connection, then execute [transit_runtime_grants.sql](../backend/sql/transit_runtime_grants.sql) for an existing `nammamove_api` group (substitute a custom group name if provisioned differently). It grants SELECT and explicitly revokes transit mutations. For new groups, the existing [runtime_role.sql](../backend/sql/runtime_role.sql) already incorporates these restrictions. Do not rerun its CREATE ROLE against an existing group. Private-schema exposure rules are unchanged. Migration introspection uses an explicit public search path, keeping `nammamove` reflection independent of the owner's name.

New tables are snapshot scoped and imported only by the owner-run CLI. Never substitute API credentials for the owner or let clients set transaction identity. The application still performs no startup migrations. See [Phase 02 status](PHASE_STATUS.md) for real migration/RLS/backup and genuine Supabase evidence. Phase 01's historical 45-test acceptance remains preserved by the enlarged suite.
