# Phase status
Last verified: 2026-11-03 (local synthetic automated checks and user-reported custom Android acceptance; no production deployment).

Current result: **52 mobile tests, 135 backend tests and 11 genuine mobile-client/Auth/API/OTP checks pass. ARM64 custom APK build/install, Google Maps and the main physical walkthrough pass by user report, including signup/sign-in, cache/relaunch/backend-loss behavior, clearing/sign-out, permissions, TalkBack, layout and Kannada/Hindi wording. Full acceptance remains pending dependency security, hosted CI and remaining lifecycle/expiry/backup/email gates.** See [current resume evidence](evidence/phase04-resume-2026-11-03.json).

| Phase | State | Evidence / next gate |
|---|---|---|
| 00 Foundation | Complete locally | Audit, root layout, roadmap, quality gates and Windows regression execution below |
| 01 Database/backend/security | Accepted locally | 45 passed, zero skipped; real PostGIS migrations/RLS/grants, backup/restore and genuine local Supabase Auth verified |
| 02 Bengaluru data | Implemented; acceptance pending external gates | Real community BMRCL import/search plus synthetic/PostGIS/Supabase tests; BMTC rights and complete authoritative coverage unresolved |
| 03 Multimodal routing | Synthetic scope verified locally; real-network acceptance blocked | Actual OTP, genuine Supabase-authenticated routing, 130 passing tests; Phase 02 external gates remain open |
| 04 Mobile/web | Automated synthetic and main device walkthrough verified; full acceptance pending | 52 mobile/135 backend/11 real-client checks pass; custom APK/Maps and user-reported walkthrough pass; security/CI and remaining lifecycle gates open |
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


## Phase 03 local fixture acceptance - 2026-10-26
- Continued the existing `phase/03-multimodal-routing` implementation without recreating, committing, pushing or merging. Phase 04 remains unstarted.
- Independently authored CC0 GTFS/geographic grid, canonical hashed inputs and official digest-pinned OTP 2.7.0 build/load are implemented. Source simulation labels, attribution and immutable graph identity remain explicit. No real Bengaluru/live coverage is claimed.
- Authenticated schedule-aware bus/metro/walking planning supports departure/arrival deadlines, weekdays/date exceptions, overnight trips, directions, transfer/walking/accessibility constraints, bounded preference ranking, known fixture fares and null unknown fares. Physical travel, initial waiting and elapsed arrival time are distinct.
- Final complete real-service regression run: **130 passed, 0 failed, 0 skipped** in 18.15 seconds, including actual PostGIS migrations/RLS/grants/spatial/atomic rollback tests, genuine local Supabase and OTP. No new schema migration is required; revision remains `0002_transit_data`.
- Ruff lint and format checks passed (71 files formatted); strict mypy passed (27 application files); pip dependency check and Git whitespace check passed. Two existing upstream warnings remain: Starlette HTTPX TestClient deprecation and Alembic geography reflection.
- Actual authenticated API workload: 40 steady-state requests, four concurrent clients, **p95 128.0 ms**, maximum 171.48 ms, zero failures; two warmups after bounded readiness probes. OTP container is limited to two CPUs, 3 GiB memory and 2 GiB Java heap. Cold graph/JIT readiness is excluded from this workload target and may return 503.
- Current graph identity: `5c8ac6db638b7245e9f2326f60184e9bdc85eada35fda7e10f913acb7acf67f7`; binary SHA-256: `834cebff7f3efd4606114b46833787fea3dc65378a2c119228ca30974a015c56`. Input hashes and aggregate measurements are recorded in [routing evidence](evidence/phase03-routing.json). Private auth settings and binary artifacts remain ignored.
- Earlier actual-service outage and retained-release rollback experiments passed on the explicitly recorded prior graph identities in that evidence: stopped provider returned 503; restart retained the artifact; old/new releases returned their respective fixture fares; mismatched graph request returned 409. These experiments are not mislabeled as executions against the final canonical-input graph.
- Reproduced cold-start timeouts were handled with bounded test readiness probes, preserving the runtime timeout and strict steady-state latency requirement. Actual arrival-boundary false negatives are handled with documented candidate padding followed by strict original-deadline filtering.

### Acceptance decision and unresolved requirements
The documented **local authored-fixture functional/performance criteria are met**. Full real Bengaluru/pilot Phase 03 acceptance is **not met**: BMTC rights/import, authoritative current station/route/direction/schedule/geographic coverage and public-content clearance remain Phase 02 blockers. Surveyed accessibility, operational lift status, city-scale workload, hosted CI execution, Linux/Python 3.12 backend validation and production security/support approval remain unverified.

Ranking is limited to returned candidates, not guaranteed global fare or walking optimality. Arrival padding is a bounded workaround; walking post-filters can conservatively omit feasible unreturned alternatives. No live overlays, congestion-safe automatic rerouting, generalized real agency fare engine, remote graph attestation or zero-downtime deployment controller is claimed. See [Phase 03 criteria](phases/PHASE_03.md), [routing runbook](ROUTING.md) and ADR-015 through ADR-018 in [decisions](DECISIONS.md).


## Phase 04 implementation and acceptance - 2026-10-27
- Continued on existing `phase/04-mobile-app`; no repository recreation, commit, push, merge or Phase 05 work. Added one Expo workspace under `apps/mobile`, npm lockfile, SDK-compatible React Native/React dependencies, strict TypeScript and client CI configuration. Existing Python/backend architecture is retained.
- Implemented onboarding, Supabase sign-in/signup confirmation handling, secure native session storage, authenticated routing with one refresh/retry, source fixture stop search, consented foreground nearby lookup/manual origin, departure/arrival time, modes/accessibility/walking constraints and four preferences. Alternatives show physical duration, waiting, known/unknown fixture fares, walking/transfers, explanations and detailed source legs.
- Geographic endpoint diagram is available without external maps; native Google basemap is optional, key-restricted and explicitly opened. Endpoint links are approximate because the API supplies no shape geometry. Saved places/recents are device-local; offline journey retention is consented, user-scoped, native-encrypted, capped and timestamped stale with a 24-hour expiry. Browser sessions/cache remain memory-only.
- Localization structure includes English and core Kannada/Hindi labels with English fallback; incomplete translation is explicit. Accessible control names/states/announcements, skeletons, no-route/error states, scalable scrollable layouts and Android Back handling are implemented. Component checks include 320/800 widths at 200% font scale, not Android layout certification.
- **31 mobile unit/component tests passed, zero failed/skipped.** Coverage includes auth/onboarding/expiry, one token refresh, refreshed-session continuity, API failures/contracts, unknown fares/no-route, permissions/manual origin, deferred loading, search selection, cache consent/expiry/isolation/corruption and encrypted chunk-write failure/Unicode session values. Native module/transport mocks are not counted as native integration evidence.
- **8 actual TypeScript client checks passed** against genuine local Supabase, a temporary non-owner FastAPI process and actual OTP: readiness, four preferences, bus-only, impossible route and invalid-token rejection. The temporary API process was stopped afterwards; no real data or credentials were written to tracked files.
- **135 backend tests passed, zero failed/skipped** in 35.17 seconds, including all real PostGIS/Supabase/OTP regressions. Five new CORS tests verify exact opt-in origins, disabled defaults, denied untrusted origins and continued bearer protection. No schema migration/API contract change is required. Python Ruff lint/format and strict mypy passed (27 application files). Existing Starlette HTTPX deprecation and Alembic geography reflection warnings remain.
- Client strict typecheck, lint, formatting, generated routing OpenAPI drift check and Expo dependency compatibility are checked; web and Android Hermes JavaScript exports are validated separately from APK/device execution. Root peer/type anchors prevent incompatible or unresolvable workspace hoisting. Latest clean-install command outcomes, test counts and source hashes are in [Phase 04 evidence](evidence/phase04-mobile.json).
- Dependency audit is **not clean**: three high affected-package entries in the Expo CLI -> Zod 3 chain remain. The app uses patched Zod 4. A forced suggested SDK-major downgrade is not applied; review an upstream compatible fix before release.

### Phase 04 acceptance decision
Local client engineering and synthetic-service integration are verified, but **not every documented criterion is met**. No Android SDK/adb/emulator was available, and no browser automation surface was connected. Native APK/AAB compilation/install, actual startup/end-to-end selection, TalkBack/large-font/keyboard/rotation, encrypted keystore/relaunch/backup/uninstall behavior, optional native basemap rendering and visual browser QA are unverified. Full Kannada/Hindi translation, signup email/deep-link delivery, hosted CI and dependency security resolution remain open.

The shared web shell supplies the commuter preview and read-only health status, not Phase 09 operations administration. Cached records require a restorable identity; expired/nonrestorable Auth can require reconnecting. Reviewed BMTC rights, authoritative current Bengaluru coverage, real paths/schedules/accessibility and production release approval remain external prerequisites. No live tracking, push subscriptions, disruption overlay or congestion-safe automatic rerouting is claimed. Follow [MOBILE.md](MOBILE.md) and [Phase 04 criteria](phases/PHASE_04.md) for manual verification; keep Phase 05 unstarted.


### Phase 04 browser Auth preflight fix - 2026-10-27
Manual browser sign-in exposed a gap in the original server-to-server integration: genuine credentials and POST headers worked, but the older local Auth server omitted CORS allowance when preflight requested `apikey`. Added a credential-free exact-origin local gateway config, preserved the previous ignored config, validated it with actual `nginx -t` and reloaded only that gateway. Both localhost preview origins now pass; an untrusted origin receives no allowance; genuine browser-header sign-in returns 200. The TypeScript integration script now includes these preflight assertions. No authentication, issuer or database authorization was bypassed. Full native/visual acceptance remains pending.

Follow-up verification: **11 real TypeScript client integration checks passed**; strict client typecheck and lint passed after the gateway regression addition. The earlier eight-check run remains historical evidence.


## Phase 04 acceptance audit - 2026-10-30
Audit-only changes on `docs/project-prd`; the working tree was clean before this audit. No application source/credentials were changed and no commit/push/merge or Phase 05 work was performed. See [machine-readable audit](evidence/phase04-audit-2026-10-30.json). The 2026-10-27 evidence is retained as historical, not copied forward as a current pass.

- Implemented in code: synthetic four-stop planning, source constraints/preferences, authenticated requests with one refresh/retry, explanations/details, endpoint diagram/optional native map, device-local favorites/recents, consented 24-hour cached journeys, manual origin/foreground permission handling, en/kn/hi translation structure, accessibility labels/loading/empty/error states. Real catalog/live coverage, complete translation, surveyed paths and native acceptance remain incomplete.
- Mobile: **31 passed, 0 failed, 0 skipped**. Strict TypeScript, ESLint, Expo dependency compatibility, web export and Android Hermes JS export passed. Exports are not APK/AAB or device evidence.
- Backend: **133 passed, 2 failed, 0 skipped** (135 total). Real PostGIS/OTP tests ran; the two genuine Auth-dependent tests fail while parsing the ignored local acceptance JSON at line 12, column 7, before sign-in. The real TypeScript integration runner also fails at bootstrap, with zero checks executed. Auth/backend/OTP HTTP health each returned 200; health is not proof that the malformed local test fixture works. Credentials and parser source excerpts are excluded from public evidence.
- Python Ruff lint/format, strict mypy and pip dependency checks passed. Existing Starlette HTTPX deprecation and Alembic geography reflection warnings remain.
- **Formatting failed in 28 mobile files.** Diagnostic normalization makes 24 pass; `eslint.config.mjs`, `jest.config.cjs`, `scripts/contracts.mjs` and `scripts/integration.mts` still differ beyond line endings. `core.autocrlf=true` and absent tracked line-ending policy contribute to checkout differences. No source reformat was performed.
- **Byte-exact routing contract check failed.** LF-normalized generated and checked-in contracts match: no semantic API schema drift was found. Fix/review line-ending policy and regenerate/check before submission.
- Fresh dependency audit: **13 low and 3 high affected-package entries, 0 critical**; security acceptance remains open. This is not a count of independent CVEs.
- Metro startup succeeded with `NODE_OPTIONS=--dns-result-order=ipv4first` and `expo start --offline --port 8081`: HTTP status and Android manifest returned 200, manifest SDK 55. Initial probe flag misuse was corrected; a default-localhost probe had timed out. Only the temporary Metro server was stopped; backend/Docker were left running. No phone was attached and no emulator was present at the standard SDK path. Native journey selection, storage lifecycle, maps and TalkBack were not verified.
- **Static finding P04-A01:** `App.tsx` `persist` catches a storage-write error and returns normally; `saveJourney` then replaces that error with a saved-success message. Existing tests cover adapter write failure but do not cover this UI false-success path. Treat reliable offline-save confirmation as incomplete until a focused behavior fix/test passes.

**Decision: full Phase 04 acceptance is not met, and submission quality gates are not all green.** Repair the private JSON without sharing credentials, normalize/review client formatting and contract output, fix the cache-save false-success path, resolve/review dependency findings and complete native/accessibility/locale evidence. Exact Android/USB/emulator instructions are in the [audited launch section](MOBILE.md#phase-04-audit-launch-commands-2026-10-30).


## Phase 04 blocker resolution - 2026-10-30
Continued on recovered `phase/04-mobile-app` (five commits ahead of its tracked remote). Preserved the four prior audit files and their historical results; no branch switch, stash application, commit, push, merge or Phase 05 work. [Follow-up evidence](evidence/phase04-followup-2026-10-30.json) supersedes the initial audit for current checks.

- Repaired accidental non-JSON text and an existing misplaced test credential in ignored local configuration. Retained the original privately and verified the intended credential against genuine Auth before restoring its field. No server password, role, JWT verification or RLS change. Private fixtures/logs remain ignored and untracked.
- Storage persistence now commits the in-memory library only after a successful write and returns an explicit outcome; offline-save success requires that outcome. Failed save/retry and failed consent writes have component regressions. Existing user-generation checks prevent stale UI success after navigation/user changes.
- Scoped mobile LF attributes and Prettier formatting remove Windows checkout inconsistencies. Contract generation resolves paths relative to its script, ignores CRLF-only differences and still rejects content drift. Explicit CRLF acceptance and semantic-mutation rejection checks passed; the contract was restored afterwards.
- Complete typed English/Kannada/Hindi UI dictionaries now cover safety/error/detail/map/date-picker text with interpolation. Tests verify key completeness, placeholders, actual Unicode script characters, missing/blank English fallback and localized screens. Fixture place names/IDs and backend attribution/explanations remain source text. Native-speaker review and native font/TalkBack validation are not established by these tests.
- Final mobile **38 passed / 0 failed / 0 skipped**. Backend **135 passed / 0 failed / 0 skipped** in 26.762 seconds, including actual disposable PostGIS, genuine Supabase ownership/roles and sealed-fixture OTP checks. All **11 actual TypeScript client checks passed** using a temporary non-owner API and existing real Auth/OTP services; only the temporary API was stopped.
- Strict TypeScript, ESLint (no warnings), Prettier, routing-contract check, Expo dependency compatibility, Ruff lint/format, strict mypy and pip consistency passed. Web and Android Hermes JS exports passed; neither is an APK/AAB or device install. Git whitespace validation passed.
- Fresh npm audit remains **13 low / 3 high affected-package entries, 0 critical**. Expo CLI requires Zod 3.25.76; app validation uses patched Zod 4.6.7. Deepmerge 4.3.1 has no published patched version. No compatible advisory fix is currently available in these chains; no forced major overrides/downgrades, suppression or lockfile churn was applied. See [advisories and scope](MOBILE.md#dependency-review-2026-10-30).
- ADB is available but reports **zero attached devices**. Native install/startup, secure-storage/relaunch/sign-out/backup/offline lifecycle, permission behavior, TalkBack/large fonts/keyboard/rotation and optional basemap remain unverified. Signup email/deep links and hosted CI also remain open. Existing BMTC rights and authoritative real Bengaluru coverage blockers remain unchanged.

**Acceptance: automated local synthetic engineering gates pass; full Phase 04 acceptance remains unmet.** Complete native/manual acceptance and review unresolved dependency findings before submission as accepted/release-ready. Use the exact [USB/emulator instructions](MOBILE.md#phase-04-audit-launch-commands-2026-10-30). No live Bengaluru coverage or Phase 05 functionality is claimed.


## Phase 04 physical map follow-up - 2026-10-31
User-reported physical passes: authentication, synthetic A-D planning/alternatives/details and simulated-data labeling; map failed. One authorized phone runs Expo Go 55.0.7 and Google Play Services. Actual logs show no captured map authorization error/fatal crash, but do not verify tiles. Fixed a confirmed app gate incorrectly requiring a project Google Maps key in Expo Go. Retained consent and the approximate endpoint-only fallback; custom binaries retain the build-time key requirement. Added explicit map width, localized fallback guidance and focused runtime/component regressions.

**45 mobile tests passed / 0 failed / 0 skipped**, with TypeScript, ESLint, Prettier, schema contract check, SDK dependency compatibility and Android Hermes JS export passing. Backend untouched; the preceding 135-pass backend result remains historical. See [map evidence](evidence/phase04-map-2026-10-31.json) and [exact phone retest](MOBILE.md#exact-usb-retest). The cause of any separate blank-Google-tile symptom is unverified until the fixed screen is retested. Native basemap acceptance, other native/human/security gates and real-source blockers remain open. Existing changes preserved; no commit, push, merge, branch switch or Phase 05.


### Confirmed blank-map cause - 2026-10-31
After opening the fixed basemap control, the user screenshot shows a blank Google-logo map. Fresh connected-device logs explicitly report **Google Android Maps SDK: Authorization failure**, identifying the host application as `host.exp.exponent` (Expo Go). The renderer initializes, but its native Maps authorization is rejected. No Maps key or raw log is included in public evidence. This verifies the visibility fix and establishes a separate actual provider-authorization blocker; coordinate/GPS permission changes are not a supported remedy.

The project cannot replace Expo Go's embedded Maps key through a JavaScript environment variable. Use an upstream repaired compatible Expo Go client, or a custom development build with an authorized Maps SDK for Android key restricted to the actual package/signing SHA-1, native rebuild and reinstall. Google project/key provisioning is owner-controlled; none was created or changed here. Keep the endpoint diagram as the available fallback, and do not mark physical map acceptance passed. No app code or tests changed in this diagnostic-only follow-up; the preceding 45 passing mobile tests do not prove tile authorization. See [map evidence](evidence/phase04-map-2026-10-31.json).


### Phase 04 custom map development build preparation - 2026-10-31
Prepared the documented react-native-maps plugin, expo-dev-client dependency, development-only EAS APK profile and sanitized configuration preflight; signing/private credential files and generated native projects are ignored. No Maps key, local signing certificate, Android SDK or cloud authorization was verified available. Actual Google project ownership/key/API/billing settings and development signing SHA-1 require manual owner configuration. Both ordinary key presence and guarded missing-key configuration checks correctly block the current environment. Existing 45 mobile regressions/static checks remain passing; Expo Go/fallback defaults are preserved. No key, billing action, EAS project/account link or signing credential was created, and no build/upload/install was started. See [exact owner steps](ANDROID_MAPS_DEVELOPMENT_BUILD.md). The physical map acceptance blocker remains open.


## Phase 04 pre-build blocker measures - 2026-11-01
The user authorized the next environment/upload measures after the read-only audit. Preserved the existing private Maps key and appended the documented USB-only API/Auth/public-gateway settings to the ignored mobile environment. Created the four previously missing EAS development variables; the Maps key is Sensitive and the three public values are Plain text. Existing cloud values were not overwritten. Fresh remote verification and cloud-only EAS config (inherited public values removed) pass; the Maps plugin receives the same key without printing it. No new Google key, billing action or signing credential was created.

Created root [.easignore](../.easignore) with all existing Git private/cache/signing protections plus unrelated backend/docs/legacy frontend exclusions. EAS's Windows copy filter receives directory names without a trailing slash; directory-only ignore patterns did not prevent an unreadable cache from being opened. Added equivalent plain directory-name patterns, then successfully ran the actual EAS filtered-copy function into a temporary directory: 46 app/workspace files, required source/manifests/lockfile retained, no private key/environment/signing/backups/caches/Git or unrelated sources. No cache was deleted or granted new permissions, no Git clone/history mutation occurred and no archive was uploaded.

Local maps:check passes. Mobile **48 passed / 0 failed / 0 skipped**; TypeScript, lint and formatting pass. API/Auth loopback values are for USB-only development and require the phone's reverse ports 8000, 54321 and Metro 8081 plus running backend/Auth/OTP. They are not hosted services and were not claimed reachable in this configuration-only step. Google Maps SDK enablement/approved billing and package/signing SHA-1 restrictions still require owner confirmation; actual installed APK tile behavior remains unverified. Existing security/native/human acceptance gates remain open.

No build, commit, push, merge or Phase 05 work. [Sanitized preparation evidence](evidence/phase04-prebuild-preparation-2026-11-01.json) records the changes.


## Phase 04 resume verification - 2026-11-03

Fresh local checks: 48 mobile tests and 135 backend tests passed with zero failures/skips; the full backend run included a new disposable PostGIS database (removed afterwards), genuine local Supabase and sealed synthetic OTP. All 11 actual mobile-client/API integration checks passed after OTP warmup. TypeScript, ESLint, Prettier, contracts, Ruff lint/format and mypy passed. Generated Android/iOS directories are now excluded from Prettier; eas.json was formatted. Existing source changes and Git history were preserved.

This chat contains user evidence of a successful ARM64 debug APK build/install and Google Maps tiles/markers on the installed custom app. This closes those specific historical blockers, not all native acceptance. Restored the existing local services, PostgreSQL-before-Auth startup ordering, IPv4 Metro binding and USB forwards on 8000/54321/8081. No credentials changed and no application database migration was run.

Current phone sign-in/signup, native storage/offline/relaunch/sign-out behavior, TalkBack/font/keyboard/rotation, human language review, hosted CI and security disposition remain pending. Full Phase 04 acceptance is not yet met; Phase 05 remains unstarted. See evidence/phase04-resume-2026-11-03.json.


### Device health-status follow-up - 2026-11-03

User confirms custom app launch. Screenshots show signed-in Plan/Settings/Saved and recent A-D/A-C entries; offline consent is off, so offline persistence is not established. Phone planning requests reach the API with HTTP 200 and server readiness returns 200. Replaced health-only AbortSignal.timeout with the AbortController/timer mechanism already used by planning; missing static API, HTTP failure and stalled-request regressions now pass. Mobile 52 passed/0 failed/0 skipped, TypeScript and lint pass; device Service status retest pending. Fresh official npm bulk advisories identify zod, minimatch, glob and deepmerge package names in the lockfile; remediation/security acceptance remains open. No forced dependency upgrade, audit suppression or completion claim.


### Physical acceptance walkthrough - 2026-11-03

User reports passes on the installed custom Android app: cached journey survives relaunch and details open; health now reports backend ready; removing only API USB forwarding leaves cached details readable and reports backend unavailable; sign-out clearing removes cached journeys and recent entries after re-login; denied location retains manual planning; Android Back works; largest device font, keyboard and landscape remain usable. Exact font scale was not measured. These are user-observed checks, not instrumented certification, and API-only disconnection does not establish fully disconnected cold-start behavior. TalkBack, native language review, signup email/deep links, backup/expiry, security and hosted-CI gates remain open. See updated resume evidence.


### Additional physical acceptance - 2026-11-03

User reports TalkBack walkthrough, Kannada/Hindi glyph/layout/navigation, and Clear saved data with continued signed-in planning pass. Natural translation quality remains unconfirmed; display success is not native-speaker review. Security/hosted CI and other unverified gates remain open as listed in resume evidence.


### Auth and translation confirmation - 2026-11-03

User confirms new-account signup/sign-in and natural accurate Kannada/Hindi wording both pass. This does not independently verify email/deep-link delivery. Completed npm audit reports 6 low/47 moderate/3 high affected-package entries and zero critical; its suggested Expo major upgrade and ESLint downgrade are not applied. Remaining CI, security and native backup/expiry gates stay explicit in resume evidence.
