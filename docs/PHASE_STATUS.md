# Phase status
Last verified: 2026-10-26 (Windows local acceptance evidence; no production deployment).

Current result: **Phase 02 implementation/audit verified locally: 87 tests passed, zero skipped. Full acceptance remains pending BMTC entitlement/import, authoritative current coverage/schedules and underlying-content clearance for public use.** Phase 01 functionality remains accepted. Current measured test and real-data evidence is recorded in the Phase 02 section below; earlier entries are historical.

| Phase | State | Evidence / next gate |
|---|---|---|
| 00 Foundation | Complete locally | Audit, root layout, roadmap, quality gates and Windows regression execution below |
| 01 Database/backend/security | Accepted locally | 45 passed, zero skipped; real PostGIS migrations/RLS/grants, backup/restore and genuine local Supabase Auth verified |
| 02 Bengaluru data | Implemented; acceptance pending external gates | Real community BMRCL import/search plus synthetic/PostGIS/Supabase tests; BMTC rights and complete authoritative coverage unresolved |
| 03 Multimodal routing | Planned | OTP graph/contract and feasibility tests |
| 04 Mobile/web | Planned | Expo/React clients and client quality gates |
| 05 Live tracking | Planned | Licensed realtime replay, freshness and privacy tests |
| 06 Disruption recovery | Planned | Trusted evidence, expiry and aggregate congestion tests |
| 07 Predictive AI | Planned | Held-out baseline/calibration and drift gates |
| 08 Payments | Planned | Provider sandbox, webhook and ledger invariants |
| 09 Operations | Planned | Load/chaos/restore and SLO evidence |
| 10 Deployment | Planned | Security review, staging, rollback and approved pilot |

## Phase 00 implementation evidence
- Inspected every original tracked file; inventory and gaps in AUDIT_PHASE_00.md.
- Removed redundant starter wrapper by moving contents to existing Git root. Existing repository, name and origin are preserved. No source feature removed.
- Retained all seven original tests; added four HTTP regression tests. Negative telemetry age now returns HTTP 422. Route choice and simulator evidence behavior remain compatible.
- Added environment/ignore rules; optional Compose now requires a locally configured password. No real secret/private credential was found in inspected source or the initial commit; no Replit runtime dependency/configuration existed.
- Separated runtime/dev dependencies; configured pytest root discovery, Ruff lint/format and strict mypy for application code.
- Added Windows/Linux CI matrix for Python 3.12 and 3.14 with read-only repository permissions; no deployment steps or credentials required.
- Windows startup instructions and all requested planning/phase files are present.

## Executed checks
Environment: Windows PowerShell, isolated .venv, Python 3.14.7.
- `python -m pytest -q`: **11 passed**, including all seven original engine regressions.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed.
- `python -m mypy`: passed, three application source files.
- `python -m pip check`: no broken requirements.
- Source credential/configuration inspection: only sample placeholders and environment references; no real secrets found.

## Validation limits and follow-up
Hosted GitHub Actions has not run; changes remain local. Python 3.12/Linux are configured CI targets, not locally verified runtime claims. Docker is not installed/available in this shell, so container builds and Compose startup were not executed; they are optional and not needed for simulator tests. Current upstream Starlette emits one HTTPX TestClient deprecation warning; tests pass, and the existing HTTPX test stack is retained rather than introducing a second client solely to suppress a warning. Dependency bounds are not a reproducible lock; reviewed locks/scanning are required before release.

## Product limits
This is still a local deterministic simulator. Demo incident/cancellation flags are not authenticated production authority. Confidence/provenance/expiry are planned. Capacity penalties do not prove aggregate congestion safety. No licensed/live data, identity, persistence, clients, ML or payments have been implemented in Phase 00.


## Phase 01 implementation and evidence - 2026-10-25
Implemented on phase/01-backend-database; no commit, push or merge performed. Phase 02 is untouched.
- Fourteen-table SQLAlchemy catalog/security schema; frozen Alembic revision and PostgreSQL/PostGIS configuration. Geography is generated from bounded coordinates and indexed with GiST.
- Private schema, RLS based on transaction-local verified identity, explicit non-owner runtime grants and separate maintenance-owner policy. No direct Supabase Data API table access is exposed.
- Supabase asymmetric JWT signature/issuer/audience/expiry/subject validation; trusted commuter/moderator/admin roles, user_metadata ignored; provider failures fail closed. No credentials or service-role keys required in source.
- Protected commuter/preferences, owned sample journeys, admin catalog writes, independent disruption verification/evidence/audit and owned notification read APIs. Legacy demo contracts are preserved and separately disableable.
- Atomic function-scoped session commits, rollback/error sanitization, 64KiB request limit, private JSON logs, request IDs and readiness checks for schema revision/PostGIS.
- Local deletion/redaction and owner-run dry-run retention command; Windows setup, role provisioning and restore instructions in DATABASE.md.

Executed on Windows/Python 3.14.7: **39 tests passed, 5 skipped**. All 11 Phase 00 tests pass. Portable tests use SQLite and generated asymmetric keys/mock JWKS transport; Alembic PostgreSQL upgrade/downgrade SQL generation passes. Ruff lint/format, strict mypy (12 app source files) and dependency consistency checks pass. Existing upstream Starlette HTTPX deprecation warning remains.

Pending external evidence: PostgreSQL/PostGIS and Docker are not installed/available in this shell. Five real database tests are opt-in and have not run locally. CI now configures a PostGIS job for spatial/constraint tests, migration roundtrip/failed-revision rollback, RLS/non-owner API/context isolation and a synthetic backup/restore drill; hosted CI has not been run or claimed successful. No genuine Supabase project/session was provided, so cryptographic verifier behavior is tested against generated keys, not a real account. Phase 01 must not be called fully accepted until these gates pass.

Remaining product/security limits: persistent catalog is manually maintained and unused by routing; only simulated journeys can be saved; no GTFS ingestion, OTP or live tracking. Basic verification records do not implement full report confidence calibration, automatic expiry/recovery or congestion control. Runtime must use a separate non-owner role; development bootstrap credentials bypass RLS. Local profile deletion does not remove Supabase Auth identity or revoke still-valid access tokens. Retention windows are provisional, maintenance is not scheduled, and production still needs rate limiting, privacy approval, reviewed dependency locks/scanning and operational secret management.


## Phase 01 acceptance retry - 2026-10-25 IST (2026-10-24 20:49 UTC)
Branch remains `phase/01-backend-database`; existing tracked modifications and untracked implementation files are preserved. No commit, push or merge performed. Phase 02 remains unstarted.

### Actual environment observations
- Windows 11 Home Single Language 64-bit, build 26200; WSL version 2.7.14, default version 2. Initial sandbox WSL enumeration was denied; read-only checks were rerun with permission and succeeded. The WSL1 optional-component warning is not evidence that WSL2 is unusable.
- `winget list --id Docker.DockerDesktop --exact --disable-interactivity`: no installed package. Docker CLI/Compose are not on PATH; Docker Desktop binaries are absent from the standard machine and per-user install paths. No Docker service/process was discovered. Supabase CLI was not found.
- TCP probe of 127.0.0.1:5432: **ConnectionRefusedError, WinError 10061**. No database is accessible at the configured local port.
- Created `.env` only after checking it did not exist. Local-only random database credentials are stored there without being printed; `git check-ignore .env` confirms it is ignored. No existing credentials or configuration were overwritten.

### Executed validation and limits
- Static YAML/Compose inspection passed: PostGIS image, loopback port, persistent volume, required password interpolation, escaped healthcheck variables and optional Redis profile. Docker CLI/daemon validation (`docker compose config --quiet`, container startup) remains blocked because Docker Desktop is absent; static inspection does not substitute for it.
- Complete local suite: **39 passed, 5 PostgreSQL integration tests skipped**, with one existing upstream Starlette/HTTPX deprecation warning. No mock or SQLite result was counted as real database acceptance.
- Ruff lint/format, strict mypy (12 app files), pip dependency consistency and Git whitespace checks pass.
- The pending non-owner integration test now executes the actual checked-in SQL grant script with an isolated test role and asserts role flags, schema privileges, migration metadata/evidence/audit restrictions and all 14 RLS-enabled tables. These assertions have not executed against PostgreSQL yet.

### Unresolved acceptance gates
| Criterion | Actual result |
|---|---|
| Docker Compose CLI and running Linux engine | Blocked: Desktop/CLI not installed |
| Authenticated PostgreSQL/PostGIS access | Blocked: TCP connection refused |
| Actual Alembic upgrade/downgrade and transactional failure recovery | Not executed on a server |
| All five PostgreSQL tests | Still skipped; no pass claim |
| Actual RLS and checked-in SQL grants | Pending real-server execution |
| Backup creation and restoration with integrity checks | Not executed; disposable-database PowerShell sequence prepared |
| Genuine local/hosted Supabase session compatibility | Unresolved; local Windows/Docker workflow is supported, but the required runtime/CLI is absent and asymmetric signing compatibility is untested |
| Portable regression tests and local quality checks | Passed as above |

**Decision: Phase 01 does not yet meet every documented acceptance criterion.** Install/start Docker Desktop manually, then execute the sequence in PHASE_01_ACCEPTANCE_WINDOWS.md. Record real outputs before closing any server/restore/Auth gate. That guide uses isolated generated test databases and container-side binary dumps; it does not delete existing databases/volumes or overwrite development work. Acceptance commands are prepared instructions, not evidence of execution. Do not proceed to Phase 02.


## Final Phase 01 local acceptance - 2026-10-25 02:52 IST
This record supersedes the earlier unavailable-Docker/database and pending-Auth outcomes. All documented Phase 01 local acceptance gates now pass; Phase 02 has not started. Branch: phase/01-backend-database. No commit, push or merge performed.

### Actual installed/running services
- WinGet registered Docker Desktop **4.96.3**. Docker CLI **29.9.2**, Compose **5.6.1**; real engine reports **linux**. First startup exceeded the CLI timeout, but a subsequent bounded engine probe succeeded. A stalled WinGet transfer recovered and completed installation; the duplicate direct transfer was stopped before launching another installer.
- `docker compose config --quiet` passed. Added Docker's newly installed bin directory to the validation command PATH so the credential helper resolves. `docker compose up -d --wait postgres` completed with container healthy.
- Authenticated TCP connection to the development database succeeded. Actual server **PostgreSQL 16.4 / PostGIS 3.4.3** from postgis/postgis:16-3.4. Real development schema revision: **0001_phase01**.
- Genuine local Supabase Auth uses official **supabase/gotrue:v2.197.0** plus **nginx:1.28-alpine**, published only on **127.0.0.1:54321**. Auth has a separate disposable database and non-superuser schema owner; the application uses another disposable database and a restricted LOGIN role. This is the actual Auth component, not a mock or a complete Supabase CLI/platform deployment.

### Executed acceptance evidence
| Gate | Real execution/result |
|---|---|
| Alembic migration | Development upgrade reached 0001_phase01; integration upgrade/downgrade and interrupted-DDL rollback passed |
| PostgreSQL/PostGIS constraints | Actual geography SRID/GiST, FK/unique/check constraints and cancellation-evidence separation passed |
| Five formerly skipped PostgreSQL tests | **5 passed**, 39 other tests deselected at that stage |
| Actual RLS and SQL grants | Checked-in runtime_role.sql executed for isolated test role; 14 RLS-enabled tables, owner isolation, no-identity denial, restricted grants and pooled identity reset passed |
| Non-owner persistent APIs | Passed on PostgreSQL; genuine Auth test also used an actual LOGIN role with no SUPERUSER/BYPASSRLS/schema ownership |
| Backup and restoration | Real custom-format pg_dump and pg_restore into a different new disposable database passed; binary-safe host copy retained under ignored backups/ |
| Restored integrity | Revision 0001_phase01; synthetic commuter count 1; restored geography SRID 4326; 14 RLS-enabled tables; dump size 49,229 bytes |
| Genuine Supabase compatibility | Actual password sign-in for three synthetic users; live public ES256 JWKS; real signature verification, trusted moderator role, malicious user_metadata rejection, invalid-token rejection and cross-user journey denial passed |
| Full automated suite with both integrations enabled | **45 passed, zero skipped**, 5.07 seconds; all 11 Phase 00 regressions included |
| Engineering gates | Ruff lint and format check passed; strict mypy passed for 12 app files; pip check passed; Git whitespace check passed |

Supabase bootstrap exposed missing prerequisites, which were corrected only in disposable Auth databases: auth schema ownership, a non-login postgres compatibility role for upstream grants, and the Auth role's search_path=auth,public before migrations. The first partially initialized database was retained for diagnosis; a fresh isolated database was used for successful acceptance. No application migration was weakened to accommodate Auth setup. No emails were sent; synthetic users were created with confirmed email through the actual local Auth admin API. No generated user access token was accepted without backend signature/claim verification.

### Evidence locations and replay
Non-secret resource names/results: ignored `backups/phase01-acceptance-state.json`. Genuine Auth runtime configuration and private acceptance credentials: ignored `backups/phase01-auth/`; never print/commit those files. The backup is also ignored. For test environment commands, use PHASE_01_ACCEPTANCE_WINDOWS.md. Auth fixture config is passed through NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG. TestClient invokes the real FastAPI app with no authentication/database overrides for the new Supabase test; Auth and PostgreSQL calls use the running services.

### Remaining limits (not failures of local Phase 01 acceptance)
One upstream Starlette HTTPX TestClient deprecation warning remains. Supabase CLI/full platform, hosted Supabase, OAuth/MFA, provider session revocation and provider-level key rotation were not validated in this local component test; existing cryptographic rotation/expiry regressions remain separate unit evidence. Hosted GitHub Actions was not run. Windows Python 3.14 was exercised; Python 3.12/Linux application jobs remain configured CI targets. Product/privacy approval of development retention windows, external Auth account deletion/revocation, production rate limits, reviewed locks/scanning, managed secrets and production recovery exercises remain pre-pilot/release requirements. Sample routing remains simulation-only and aggregate congestion safety is still a future release gate.

**Decision: Phase 01 meets its documented local acceptance criteria.** No production-readiness or live-transit claim is implied. Do not start Phase 02 without the next explicit instruction.

Acceptance database identifiers (synthetic resources only):
- test_database: `nammamove_acceptance_9c1aa2778fb64f27aaba9200d818662f_test`
- backup_source: `nammamove_backup_66a676cad81540e487600ed3fc3e93c2_test`
- restore_target: `nammamove_restore_a891509680674ba39a91df7d8187d814_test`
- supabase_auth_database: `nammamove_supabase_auth_7890c95566f04b33b356fbf9dbf67122_test`
- supabase_api_database: `nammamove_supabase_api_9d5850f0461a4f8c8c83061eea95e2da_test`


## Phase 02 implementation and acceptance evidence - 2026-10-26
Branch: `phase/02-transit-data`. Existing repository and Phase 00/01 behavior preserved. No Phase 03, commit, push or merge.

Implemented thirteen additive snapshot tables; bounded fixed-route GTFS validation; owner-only staged/idempotent import, quarantine, concurrent refresh serialization, atomic promotion and retained-version rollback; explicit BMTC/BMRCL adapters; protected feed/stop/route/pattern/transfer/network APIs; actual PostGIS proximity search; source/license/timestamps/coverage and community quality notes; SELECT-only runtime RLS/grants. Readiness requires the new head. Alembic private-schema reflection now works when owner username equals schema name.

Executed on Windows/Python 3.14.7, PostgreSQL 16.4/PostGIS 3.4.3 and genuine official local Supabase Auth v2.197.0:
- `python -m pytest -q -p no:cacheprovider --tb=short` with the ignored real-service environment configured: **83 passed, zero skipped**, in 22.35 seconds: 74 portable behavioral tests, 8 genuine PostgreSQL integration tests and 1 genuine Supabase Auth integration test. All accepted Phase 00/01 regressions remain passing. Synthetic ZIP fixtures use fixed metadata timestamps so byte-checksum idempotence tests are deterministic.
- `python -m ruff check .` and `python -m ruff format --check .`: passed (57 Python files formatted).
- `python -m mypy`: passed, 20 application source files under strict checking.
- `python -m pip check`: no broken requirements. `docker compose config --quiet` and `git diff --check`: passed.
- Tracked/untracked deliverables scan found no private-key blocks or recognizable JWT/Supabase secret-token values. `.env`, private Auth acceptance credentials, community feed and dump paths were confirmed ignored. No claim that pattern scanning alone proves absence of every possible secret.
- Final validator rechecked the downloaded real community BMRCL ZIP; normalized counts match the successful database import.
- Alembic upgrade applied to local development and the isolated Supabase acceptance database; real fixture roundtrips/failure rollback executed. `alembic check`: no new upgrade operations detected.
- Actual migration failure injection leaves Phase 01 intact. Actual mid-import SQL failure leaves active dataset and normalized row counts intact. Concurrent identical refreshes resolve to one version.
- New spatial search uses genuine geography, SRID 4326 and GiST; non-owner identity checks and SELECT-only grants are exercised against PostgreSQL, not SQLite.
- Genuine Supabase sign-in/JWKS and protected transit access pass alongside existing ownership, verification and simulator regressions.
- Executed disposable backup/restore: 93,747-byte synthetic dump, new head, two transit stops, identical active pointer, SRID 4326, 27 RLS-enabled tables restored.

Real data: pinned ODbL community BMRCL snapshot successfully validated/imported into a disposable database: 488 stop records, 3 routes, 3,279 trips, 88,906 stop times, 19 shapes, 16 transfers, one weak component. Repeat CLI import, explicit activation and genuine-auth/non-owner spatial, route, date-filtered pattern and transfer queries passed. Source-derived intermediate times are estimates, not observed arrivals; dataset publication timestamp is unknown. Raw data remains ignored. See [Phase 02 evidence](phases/PHASE_02.md), [source/runbook](TRANSIT_DATA.md) and [aggregate JSON](evidence/phase02-community-bmrcl.json).

Synthetic data: all committed GTFS fixtures, malformed-feed/failure/concurrency tests, realtime freshness inputs and backup source rows are explicitly authored test data. Existing seven-edge journey planning remains simulation. No official/live feed, cross-provider pedestrian graph or OTP integration is enabled.

Unresolved acceptance requirements: BMTC publisher's ODbL declaration includes content-rights caveats requiring review/authorization before importing/distributing its contents; no reviewed representative BMTC import has passed. Official provider access and independent current city-wide schedules/coverage/interchanges/accessibility remain unverified. Refresh is manual; fixed-route GTFS profile omits optional fare/pathway/translation/feed_info semantics and rejects unsupported features. Structural connectivity is not timed transfer feasibility or congestion-safe assignment. Hosted CI, Linux/Python 3.12 execution and hosted/full Supabase platform remain unverified locally. Upstream Starlette HTTPX deprecation remains; Alembic may warn about reflection of generated geography, which is explicitly excluded from ORM comparison and exercised by real spatial tests.

**Phase 02 does not meet every acceptance requirement. Do not begin Phase 03 until unresolved source/coverage gates are closed or explicitly revised with product approval.**


## Phase 02 acceptance audit - 2026-10-26
This audit supersedes the earlier 83-test count as the latest run, without changing its historical evidence. Branch remains `phase/02-transit-data`; all prior uncommitted work is preserved. No commit/push/merge, restricted scraping, production dataset import or Phase 03.

- [Rights registry](DATA_SOURCES.md) now distinguishes publisher-declared ODbL database rights from unverified BMTC content rights; historical OpenBangalore/geohacker, OpenCity and TUMI data are not assumed cleared. Official agency permissions/access contracts were not established. No BMTC feed was downloaded/imported. BMRCL's prior community evaluation does not by itself clear all underlying contents for public deployment; agency copyright-policy ambiguity is explicitly recorded.
- Sampled official BMRCL maps corroborate corridor termini and two interchange locations. A dated government release corroborates Yellow's sixteen stations at inauguration. Retrieved official timetable HTML did not expose usable numeric schedules; exhaustive current station/platform/direction/time/geographic certification remains open. No invented timetable replacements.
- Read-only real-data audit: 1 community operator, 3 routes, 83 station records, 170 platforms, 235 entrances, 3,279 trips, 88,906 stop times and 16 transfers. Route memberships 32/37/16 share two stations. Internal reverse patterns pass, 25 overnight trips have no time regressions, reference/coordinate checks found zero errors. No actual BMTC inventory is inferred from zero imported records.
- One weak component versus **151 strong components** over platform ride/explicit-transfer edges (independently cross-checked): this catalog lacks a complete station/pedestrian/accessibility graph and cannot certify all-pairs journeys. The development database still has zero active static feeds; the real source remains in its disposable evaluation database.
- All 88,906 imported stop times have `timepoint=0`. Pattern API now exposes source timepoint and approximate/source-timepoint labels, plus false agency schedule-verification metadata. Existing fields and quality notes are preserved; no times changed or live status inferred.
- **87 passed, zero skipped**, including 8 genuine PostgreSQL tests and 1 genuine Supabase Auth test; all Phase 00/01 regressions retained. New behavioral tests verify approximate labels, read-only audit and strong-versus-weak distinction. Actual malformed import, concurrency, SQL failure and RLS/grant tests preserve last-known-good behavior. Ruff lint/format, strict mypy (21 app files) and pip consistency pass. Existing two upstream warnings remain nonfatal.

[Final audit](PHASE_02_ACCEPTANCE_AUDIT.md) and [aggregate coverage evidence](evidence/phase02-network-coverage.json) contain comparison scope, reproducible read-only command, known gaps and next steps. Use only authored, clearly simulated fixtures in a separate simulation pointer/disposable database while external dependencies remain pending. That fallback does not satisfy real-data acceptance or authorize Phase 03. **Full Phase 02 acceptance is not met.**

Final audit verification: full suite **87 passed, zero skipped in 16.24 seconds**; lint, format, strict mypy and pip checks passed. A further read-only genuine-auth/non-owner request against the retained real BMRCL snapshot verified approximate labels on every stop in the sampled pattern. Maps, feed archive and Auth credentials remain ignored. No snapshot/pointer mutation was performed by the audit.
