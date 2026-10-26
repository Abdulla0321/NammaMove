# Phase 01 - Database, Backend and Security
Status: Accepted locally on 2026-10-25. 45 tests passed with zero skips, including real PostgreSQL/PostGIS and genuine local Supabase Auth. See ../PHASE_STATUS.md for final evidence. Phase 02 was unstarted at that acceptance; current work is recorded separately in [PHASE_02.md](PHASE_02.md).

## Prerequisites
Phase 00 accepted. A PostgreSQL/PostGIS server and Supabase asymmetric signing-key project are needed for external verification. Provisional development retention windows are documented; product/privacy approval is required before production use.

## Implementation tasks
- [x] Introduce SQLAlchemy, PostgreSQL/psycopg, PostGIS schema and frozen Alembic migration.
- [x] Define 14 tables for commuters/preferences, operators/stops/routes/trips/stop times, snapshots, vehicles, journeys, disruptions/evidence, notifications and audit.
- [x] Add generated stop geography/GiST index, constraints, scoped external IDs and independent cancellation evidence.
- [x] Integrate Supabase ES256/RS256 JWKS validation, subject/issuer/audience/time checks and trusted role dependencies.
- [x] Add protected /v1 APIs, owner isolation, independent moderation and atomic audited writes.
- [x] Add private-schema RLS policies and separate runtime privilege provisioning.
- [x] Add JSON request logging, bounded bodies, safe error responses, liveness and database readiness.
- [x] Add explicit privacy deletion/redaction and dry-run retention; document maintenance and backup/restore.
- [x] Preserve Phase 00 simulator and all existing regressions; default simulation off in production.
- [x] Add portable behavioral tests, PostgreSQL opt-in integration tests and CI service/restore drill.
- [x] Execute real PostgreSQL/PostGIS migration upgrade/downgrade, RLS, failure rollback and API tests.
- [x] Record successful backup/restore drill and genuine Supabase token verification with separate runtime login.

## Expected deliverables
Persistent API modules, Alembic config/frozen revision, PostGIS setup, runtime grants, auth/ownership/error tests, retention command, CI integration job and Windows runbook in ../DATABASE.md. Development credentials remain outside Git.

## Edge cases
Expired/future/forged JWT, missing claims, wrong issuer/audience, key rotation/revocation/outage, anonymous/service-role tokens, malicious user metadata, cross-user IDs, absent profile, invalid coordinates, duplicate external IDs, body over 64KiB, independent moderation, expired evidence, unavailable GPS, DB outage, commit failure, interrupted migration, local deletion and referenced cancellation evidence during retention.

## Automated tests
Portable tests exercise actual JWT cryptography with generated keys/mocked JWKS, API ownership/roles, strict inputs, transactional failures, redaction/retention and preserved routing. Offline Alembic SQL generation checks migration structure. Five opt-in PostgreSQL tests (executed successfully) verify actual spatial types/indexes, FK/unique/check constraints, upgrade/downgrade, non-owner RLS and pool context reset, persistent APIs/readiness and failed-revision rollback. A real local backup/restore integrity drill passed. An additional opt-in Supabase test uses actual password sign-in and ES256 JWKS with a restricted database login; it passed in the full 45-test run. CI also configures a backup/restore drill, which has not been run on GitHub. SQLite is not evidence of PostgreSQL/RLS behavior.

## Completion criteria
Applicable local gates pass with all Phase 00 assertions preserved. Database acceptance requires successful PostgreSQL suite and restore execution on a real server; Auth interoperability requires a genuine Supabase access token. All three requirements were satisfied locally on 2026-10-25. Do not mark these gates passed from generated SQL or configured CI alone. Document results and approved runtime/retention configuration in PHASE_STATUS.md.

## Safety gate
Missing GPS means uncertainty, never cancellation. Vehicle cancellation has a separate evidence FK; future ingestion must verify that evidence's authority and freshness. Persistent incident reports start unverified and only independent trusted moderators can append verification evidence; these records do not alter any routing graph in this phase. Simulation/live labels are explicit. Aggregate congestion-safe rerouting remains gated in Phase 06. No live feeds or Phase 02 ingestion were introduced by Phase 01; see the separate Phase 02 record for current static catalog work.
