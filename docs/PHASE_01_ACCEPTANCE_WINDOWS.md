# Phase 01 acceptance on Windows - real services only

## Current state (2026-10-25 IST)
**Phase 01 is now accepted locally: 45 tests passed, zero skipped.** Docker Desktop 4.96.3, Docker CLI 29.9.2 and Compose 5.6.1 are installed; the Linux engine and PostgreSQL/PostGIS are running. Real migration/RLS/grant checks, backup/restore and official local Supabase Auth ES256/JWKS verification passed. See PHASE_STATUS.md for the final dated evidence. Installation commands below are for initial setup, not a request to reinstall the working system.

The repository stays on phase/01-backend-database; previous work is preserved and no commit/push/merge was performed. Local passwords, Auth keys, synthetic-user credentials and dumps exist only in ignored files. Do not overwrite .env or print resolved Compose configuration containing secrets. Database port 5432 and Auth gateway 54321 are loopback-only.

## 1. Manual Docker Desktop setup
In Windows PowerShell:
```powershell
winget install --exact --id Docker.DockerDesktop
```
Complete any installer prompts. If WinGet is unavailable, use the installer from [Docker's Windows instructions](https://docs.docker.com/desktop/setup/install/windows-install/). Start Docker Desktop from the Windows Start menu, complete first-run prompts and choose the **WSL 2 / Linux containers** backend. Wait for **Engine running**. Restart Windows only if the installer requests it; do not reboot during unsaved work.

If Docker reports a WSL prerequisite problem, run the following from Administrator PowerShell as applicable, then follow its restart instructions:
```powershell
wsl --version
wsl --update
wsl --set-default-version 2
# Only if WSL/Virtual Machine Platform features are reported missing:
wsl --install --no-distribution
```
Enable hardware virtualization in BIOS/UEFI if Docker reports it disabled. Do not install a second PostgreSQL service to mask a Docker engine failure. Docker Desktop includes Compose; no separate Compose install is needed.

Open a new ordinary PowerShell after installation:
```powershell
cd "$HOME\Desktop\NammaMove"
docker version
if ($LASTEXITCODE -ne 0) { throw 'Docker engine is not ready' }
docker info --format '{{.OSType}}'
docker compose version
```
`docker version` must show both Client and Server; OSType must be `linux`. If only the client works, start/restart Docker Desktop. If `docker` is missing from the new shell, check the install directory and installer PATH setup; do not change the repository to work around it.

## 2. Validate Compose and start the development database
These commands assume the prepared local defaults POSTGRES_USER=nammamove and POSTGRES_DB=nammamove. If your existing `.env` uses different names/port, adapt the corresponding commands; never replace an existing password just to match this guide.
```powershell
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed' }
docker compose up -d --wait postgres
if ($LASTEXITCODE -ne 0) { throw 'Postgres startup/health check failed' }
docker compose ps
docker compose exec -T postgres pg_isready -U nammamove -d nammamove
if ($LASTEXITCODE -ne 0) { throw 'Postgres is not ready' }
```
Port 5432 is loopback-only, storage uses named volume pgdata, and Redis is outside the default profile. Do not run `docker compose down -v`, volume removal, database reset or password replacement against existing storage. An existing volume keeps its original initialization credentials even if `.env` changes. If health/startup fails, inspect `docker compose logs --tail 60 postgres` locally; review/redact logs before sharing.

## 3. Verify authenticated TCP access and apply migrations
Load the migration-owner DATABASE_URL from ignored `.env` into this PowerShell session without printing it:
```powershell
$env:PYTHONPATH = 'backend'
$env:DATABASE_URL = & .\.venv\Scripts\python.exe -c "from app.config import Settings; s=Settings(); assert s.database_url; print(s.database_url.get_secret_value())"
if ($LASTEXITCODE -ne 0) { throw 'DATABASE_URL configuration failed' }
.\.venv\Scripts\python.exe -c "import os,psycopg; c=psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1),connect_timeout=5); print(c.execute('SELECT current_database(), current_user').fetchone()); c.close()"
if ($LASTEXITCODE -ne 0) { throw 'Authenticated database access failed' }
.\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop and inspect before proceeding' }
.\.venv\Scripts\python.exe -m alembic current
docker compose exec -T postgres psql -U nammamove -d nammamove -v ON_ERROR_STOP=1 -c 'SELECT postgis_full_version(); SELECT version_num FROM nammamove.alembic_version;'
```
Expected revision: `0001_phase01`. Do not echo DATABASE_URL or run `docker compose config` without `--quiet`. The bootstrap identity is for migrations; it bypasses RLS and must not serve protected APIs. Configure the separate runtime login using DATABASE.md before running the application.

## 4. Run all five real database tests and the full suite
Use a new empty disposable test database. Names below contain only generated identifier-safe characters and end in `_test`. If creating a name fails, stop rather than reusing another database.
```powershell
$testDb = 'nammamove_acceptance_' + [Guid]::NewGuid().ToString('N') + '_test'
docker compose exec -T postgres createdb -U nammamove $testDb
if ($LASTEXITCODE -ne 0) { throw 'Disposable test database creation failed' }
$env:NAMMAMOVE_TEST_DATABASE_URL = & .\.venv\Scripts\python.exe -c "import os,sys; from sqlalchemy.engine import make_url; print(make_url(os.environ['DATABASE_URL']).set(database=sys.argv[1]).render_as_string(hide_password=False))" $testDb
if ($LASTEXITCODE -ne 0) { throw 'Test database URL configuration failed' }
.\.venv\Scripts\python.exe -m pytest -q -m postgres
if ($LASTEXITCODE -ne 0) { throw 'Real PostgreSQL acceptance tests failed' }
.\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Complete test suite failed' }
.\.venv\Scripts\python.exe -m ruff check .
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
.\.venv\Scripts\python.exe -m ruff format --check .
if ($LASTEXITCODE -ne 0) { throw 'Format check failed' }
.\.venv\Scripts\python.exe -m mypy
if ($LASTEXITCODE -ne 0) { throw 'Type check failed' }
.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
```
Required results: five real PostgreSQL tests pass with no database skips; the suite now contains 45 tests; set the genuine Supabase acceptance config below to avoid an Auth skip. The tests apply/downgrade migrations, validate PostGIS geography/indexes, enforce FK/unique/check constraints, test failed-DDL rollback and prove owner isolation/transaction-local context clearing. The non-owner test executes backend/sql/runtime_role.sql with an isolated role and asserts no superuser/BYPASSRLS/role-creation privileges, no schema creation, read-only migration metadata, immutable evidence/audit privileges and RLS enabled on all 14 application tables. Generated JWTs/mock JWKS in the API test fixture cover only the API/database boundary; they do not satisfy real Supabase acceptance.

Test fixtures refuse existing nammamove schemas and clean up their own schema after each test. If a failed run leaves a schema behind, preserve it for diagnosis and create a new disposable database for the next run. Do not aim these tests at the development or a production database.

## 5. Create and restore a real backup, safely in PowerShell
Use two additional new disposable databases; never restore over development data. Keep binary pg_dump/pg_restore inside the Linux container. Use `docker compose cp` for a binary-safe host copy; Windows PowerShell 5.1 native binary pipelines/redirection can corrupt a dump.
```powershell
$migrationUrl = $env:DATABASE_URL
$backupDb = 'nammamove_backup_' + [Guid]::NewGuid().ToString('N') + '_test'
$restoreDb = 'nammamove_restore_' + [Guid]::NewGuid().ToString('N') + '_test'
$dumpFile = $backupDb + '.dump'
docker compose exec -T postgres createdb -U nammamove $backupDb
if ($LASTEXITCODE -ne 0) { throw 'Backup source database creation failed' }
docker compose exec -T postgres createdb -U nammamove $restoreDb
if ($LASTEXITCODE -ne 0) { throw 'Restore target database creation failed' }
try {
    $env:DATABASE_URL = & .\.venv\Scripts\python.exe -c "import os,sys; from sqlalchemy.engine import make_url; print(make_url(os.environ['DATABASE_URL']).set(database=sys.argv[1]).render_as_string(hide_password=False))" $backupDb
    if ($LASTEXITCODE -ne 0) { throw 'Backup database URL failed' }
    .\.venv\Scripts\python.exe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Backup fixture migration failed' }
    docker compose exec -T postgres psql -U nammamove -d $backupDb -v ON_ERROR_STOP=1 -c "INSERT INTO nammamove.commuters (id,created_at,display_name,locale,location_consent) VALUES ('00000000-0000-0000-0000-000000000001',now(),'Synthetic restore fixture','en',false)"
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic fixture insert failed' }
    docker compose exec -T postgres pg_dump -U nammamove -d $backupDb -Fc -n nammamove -f "/tmp/$dumpFile"
    if ($LASTEXITCODE -ne 0) { throw 'Backup creation failed' }
    New-Item -ItemType Directory -Path backups -Force | Out-Null
    docker compose cp "postgres:/tmp/$dumpFile" "backups/$dumpFile"
    if ($LASTEXITCODE -ne 0) { throw 'Binary backup copy failed' }
    docker compose exec -T postgres psql -U nammamove -d $restoreDb -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS postgis'
    if ($LASTEXITCODE -ne 0) { throw 'Restore PostGIS initialization failed' }
    docker compose exec -T postgres pg_restore -U nammamove -d $restoreDb --no-owner --exit-on-error "/tmp/$dumpFile"
    if ($LASTEXITCODE -ne 0) { throw 'Restore failed' }
    docker compose exec -T postgres psql -U nammamove -d $restoreDb -v ON_ERROR_STOP=1 -c "SELECT version_num FROM nammamove.alembic_version; SELECT 1/count(*) AS fixture_present FROM nammamove.commuters WHERE display_name='Synthetic restore fixture'; SELECT count(*) AS rls_enabled_tables FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='nammamove' AND c.relkind='r' AND c.relrowsecurity;"
    if ($LASTEXITCODE -ne 0) { throw 'Restore integrity check failed' }
} finally {
    $env:DATABASE_URL = $migrationUrl
    Remove-Variable migrationUrl -ErrorAction SilentlyContinue
}
```
Expected outputs: revision `0001_phase01`, fixture_present `1`, rls_enabled_tables `14`. Record source/target database names, backup path, timestamp, exit statuses, revision and integrity counts in PHASE_STATUS.md. Do not record URLs, passwords, user tokens or personal records. No cleanup command deletes databases/volumes automatically; keep only the synthetic disposable evidence needed for review. Restored runtime grants must also be reviewed before any production recovery claim.

## 6. Genuine local Supabase Auth - verified
The accepted local environment uses the official supabase/gotrue:v2.197.0 Auth image, nginx:1.28-alpine gateway and an isolated PostgreSQL Auth database. Configuration follows the [official self-hosted Auth signing-key guide](https://supabase.com/docs/guides/self-hosting/self-hosted-auth-keys) and [official Docker service configuration](https://github.com/supabase/supabase/blob/master/docker/docker-compose.yml). This is a genuine Auth component deployment, not a mock, Supabase CLI project, hosted Supabase project or complete platform deployment.

The ignored local files under backups/phase01-auth contain generated private signing keys/configuration, synthetic credentials and the non-owner API database URL. Do not copy them into source control or display their content. The upstream Auth DB prerequisites are: a separate database with non-superuser owner, auth schema owned by that role, search_path=auth,public established before first migration, and a non-login postgres compatibility role for upstream grants. Failed bootstrap databases were preserved; a fresh isolated DB was used after correcting prerequisites. Neither the development app schema nor authentication validation was weakened.

To restart the already provisioned local component:
```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
docker compose up -d --wait postgres
docker compose -f backups/phase01-auth/compose.yaml up -d --wait
```
If Docker used a per-user install, use that installation's resources/bin directory instead. No private key or token is needed on the command line. Do not run a reset/re-initialization command against these existing databases.

To rerun **all 45 tests with both integrations enabled** on this machine, load the existing disposable test database name and private acceptance configuration without printing credentials:
```powershell
$env:PYTHONPATH = 'backend'
$env:NAMMAMOVE_TEST_DATABASE_URL = & .\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from app.config import Settings; from sqlalchemy.engine import make_url; s=Settings(); assert s.database_url; state=json.loads(Path('backups/phase01-acceptance-state.json').read_text()); print(make_url(s.database_url.get_secret_value()).set(database=state['test_database']).render_as_string(hide_password=False))"
if ($LASTEXITCODE -ne 0) { throw 'Test database URL configuration failed' }
$env:NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG = Join-Path (Get-Location) 'backups/phase01-auth/acceptance.json'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw 'Acceptance tests failed' }
```
The dedicated test may be selected with `-m supabase`. It signs in three actual synthetic accounts through the real Auth password endpoint, obtains genuine ES256 tokens and verifies the live JWKS via the unmodified application verifier. It uses a real restricted PostgreSQL LOGIN with no database/auth dependency overrides. It checks readiness, profiles, owner isolation, malicious user_metadata rejection, trusted independent moderation and invalid-token rejection. No user access tokens are minted by the test or stored in the acceptance configuration. Tests without the required real-service configuration skip explicitly; a skipped result does not renew acceptance evidence.

Fresh-machine recreation needs new isolated Auth/app databases, generated EC signing keys and synthetic confirmed accounts provisioned through the actual local Auth admin API. Keep `GOTRUE_JWT_KEYS` private and configure issuer http://127.0.0.1:54321/auth/v1 consistently with the gateway route. Do not accept HS256 in the NammaMove verifier or disable signature validation. Never reuse acceptance accounts/passwords/keys for a real pilot. Full Supabase CLI/hosted behavior, OAuth/MFA, online revocation and provider-level key rotation were not exercised by this component test and remain pre-production scope checks.

## Acceptance decision
**Phase 01 meets its documented local acceptance criteria.** Actual Docker/Compose, PostgreSQL/PostGIS migrations/RLS/grants, binary backup/restore and genuine local Supabase Auth passed, followed by 45 tests with zero skips and all quality checks. Hosted CI and production readiness are separate, unclaimed gates. Preserve Phase 02 as not started. No commit, push or merge is part of this procedure.
