# Architecture decisions
## ADR-001 ? Flatten existing starter wrapper (accepted, Phase 00)
The wrapper contained all source with no independent package purpose. Move its contents into the existing Git root, preserve history and backlog, and update commands. No new repository or project is created.

## ADR-002 ? Modular monolith and progressive stack (accepted)
Retain FastAPI and the simulator. Add database/auth, OTP, clients, realtime and ML in their phases. Compose services remain optional and disconnected for now. Avoid premature services and unused dependencies.

## ADR-003 ? Separate truth from freshness (accepted)
Missing GPS cannot establish cancellation. Production verification needs authorized evidence, confidence and expiry. Preserve demo flags for compatibility, clearly labeled; replace their trust boundary before live deployment.

## ADR-004 ? Congestion is a release constraint (accepted)
Static crowding penalties are illustrative, not network assignment. Require aggregate replay, capacity-aware throttling and cooldown before live automatic recovery. Individual shortest paths do not prove network safety.

## ADR-005 ? Foundation quality gates (accepted)
Use pytest/HTTPX, Ruff lint/format and strict mypy for application code. CI spans Windows/Linux, Python 3.12/3.14. Separate runtime/dev requirements. TypeScript gates start when clients exist. Current dependency bounds are not locks; reviewed reproducible locks and vulnerability scans are required before release.

## ADR-006 ? Environment independence (accepted)
No Replit dependency/configuration exists, so no replacement is needed. Use standard Python/Uvicorn and optional Docker. Simulator needs no secrets. Compose requires an ignored local password; future URLs remain documented, unconnected configuration. Ignore rules do not prove tracked content is secret-free.

## ADR-007 - Private persistent APIs and database identity (accepted, Phase 01)
Add versioned /v1 endpoints; preserve Phase 00 simulation contracts separately. PostgreSQL/PostGIS is the only configured runtime persistence engine. Use SQLAlchemy synchronous bounded pools, Alembic frozen migrations and generated spatial geography. SQLite is exclusively a portable test double. No implicit migrations on startup. Commit inside function-scoped dependencies before sending success.

## ADR-008 - Supabase asymmetric verification and roles (accepted, Phase 01)
Use PyJWT with configured project JWKS, ES256/RS256 allowlist, required issuer/audience/time/subject and authenticated user role. Never trust token-provided key URLs, unsigned claims or user_metadata. Server-managed app_metadata.nammamove_role grants commuter/moderator/admin. No shared secret, service-role token or password verifier is introduced. Cache key sets briefly without permanent key caching; fail closed on provider failure. Real Supabase interoperability remains an explicit validation gate.

## ADR-009 - Non-owner API connections and transactional RLS context (accepted, Phase 01)
Use private nammamove schema, deny PUBLIC grants, enable RLS and set verified identity transaction-locally. Deploy with a dedicated non-owner/non-BYPASSRLS login, not Docker bootstrap credentials. API checks enforce ownership and independent moderation in addition to RLS. Clients cannot connect directly or set database identity. A separate owner identity runs migrations/retention. Table owners bypass RLS and must never be production runtime identities.

## ADR-010 - Privacy and provisional retention (accepted for development)
Do not duplicate Auth passwords/emails or collect raw GPS history. Local deletion removes owned history and redacts reporter text; it does not delete the external Supabase account. Retention CLI defaults to dry-run: 30-day journey/notification, 90-day audit/inactive-disruption windows, preserving referenced cancellation evidence. Obtain product/privacy approval and full account-deletion procedures before pilot release. No automatic background deletion is scheduled.


## ADR-011 - Snapshot-scoped static catalog (implemented, Phase 02)
Add thirteen tables and `/v1/transit` APIs instead of rewriting Phase 01 catalog IDs or simulator contracts. Separate pointers for provider and scheduled/simulation mode. Serialize owner imports with advisory transaction locks; stage/promote atomically, retain previous versions, quarantine invalid metadata and roll back SQL failures. Runtime grants are SELECT-only, including admin identities. Validated historical versions remain readable under RLS so an API request can finish against a snapshot selected before concurrent promotion; searches expose only the active version. Private tables remain unavailable through Supabase Data API.

## ADR-012 - Explicit source review and bounded GTFS profile (implemented, Phase 02)
No default official/live source or scraping pipeline is assumed. Require owner-reviewed provenance, license/authorization reference, checksum, timestamps and community quality notes. HTTPX downloads are explicit, bounded and credential-free; raw feeds/dumps stay ignored. Support the documented fixed-route subset and report unsupported optional tables rather than manufacture information. Frequency windows and untimed intermediate stops retain uncertainty. A manifest does not prove legal entitlement, and community schedules do not establish actual operational service.

## ADR-013 - Structural catalog before journey integration (implemented, Phase 02)
Use genuine PostGIS geography for proximity searches, explicit source directions/transfers and calendar exceptions for catalog inspection. Report directed edges and weak components without inferring reverse trips, walking links, accessible station paths, live cancellations or network-safe rerouting. GTFS-RT freshness is only a contract here; workers/Redis remain Phase 05 and OTP remains Phase 03. City-wide and provider acceptance are separate from passing synthetic/database tests.


## ADR-014 - Evidence-scoped acceptance and approximate timing (Phase 02 audit)
Retain static data as unverified operational evidence: expose timepoint=0 as approximate and type 1 as a source timepoint, never an observed arrival guarantee. Report weak and strong graph components separately; avoid certifying routing from a weakly connected platform catalog. Add a read-only aggregate audit rather than enabling routing or writing a new source. Publisher license assertions do not close underlying-content rights; record unresolved access/permissions and keep source-free synthetic fixtures separate until source/coverage acceptance is satisfied. See [acceptance audit](PHASE_02_ACCEPTANCE_AUDIT.md).


## ADR-015 - User-authorized synthetic Phase 03 exception
Proceed on the existing Phase 03 branch using independently authored GTFS and CC0 geographic content, under the latest explicit instruction. This does not close Phase 02 data entitlement/coverage gates. No external licensed feed or real OSM content is required for this engineering fixture; geographic values/streets are illustrative. Permit local fixture acceptance only, preserving production and real-network blockers.

## ADR-016 - Pinned OTP, immutable inputs and explicit rollback
Use official OTP 2.7.0 linux/amd64 pinned by digest behind a typed GraphQL provider protocol; preserve all legacy APIs. Hash canonical inputs/image, validate GTFS/source metadata and record graph binary hash after a successful build. Construct a provider only from a verified sealed release. Use explicit canary/coordinated release and previous-release rollback, not silent stale-graph/simulator fallback. Local service/mount verification is operational; cryptographic remote graph attestation and zero-downtime activation are not claimed.

## ADR-017 - Bounded preference ranking and honest schedule semantics
OTP performs schedule/street search; the application validates chronology/continuity/transfers and post-filters hard limits. Rank only returned candidates for time/fare/transfers/walking, with explicit scope instead of global optimality claims. Keep generalized costs out of physical duration; show initial waiting separately. Known fixture fares are source-derived per boarding, unknown remains null. Source wheelchair constraints are not live lift assurance. Use bounded arrival-window padding for a reproduced OTP 2.7 false negative, then enforce the caller's exact deadline; document possible completeness limits.

## ADR-018 - Local acceptance workload and privacy
Use at most four provider calls per process, a 1.5s inactivity timeout, 2 MB response budget, 16 candidates and 64 legs. Benchmark the actual authenticated endpoint at four concurrency/40 warm requests, with graph loading/JIT treated as readiness. No raw coordinates/tokens are logged or persisted by the backend. Fixture routing is opt-in and disabled in production. Retain real-service fault/rollback evidence; neither mocks nor skipped integration tests establish OTP acceptance. No production sizing/cancellation/rerouting guarantees arise from this workload.


## ADR-019 - One Expo commuter workspace and bounded web shell (Phase 04)
Add `apps/mobile` to the existing monorepo, with Expo SDK 55, strict TypeScript, React Native and a shared React Native Web commuter/status preview. Do not introduce a separate operations administration product before its gate. Pin compatible React/RN peers in the root and commit the npm lockfile; generate routing types from the real FastAPI schema and check contract drift. Keep authorized synthetic stop search independent of the unsynchronized persistent catalog. Native maps supplement a geographic endpoint/list fallback, never manufacture missing shapes.

## ADR-020 - Device privacy, explicit stale cache and token lifecycle
Use Supabase public-client auth only, encrypted native SecureStore sessions and a serialized chunked adapter; web storage is memory-only. Refresh once after 401, fail closed and clear user-visible results on invalid sessions; token refresh for the same user must not erase the selected itinerary. Favorites/recents are user-scoped device records; offline journey retention is explicit consent, capped and expires after 24 hours. Sign-out removes device records. No location history or background tracking; permission denial retains manual origin. Native key/backup/uninstall/orphan cleanup requires device/pilot review.

## ADR-021 - Evidence-scoped Phase 04 acceptance
Component accessibility/width/font-scale assertions and web/Android JavaScript exports are not proof of native installation, TalkBack or real basemap behavior. Require physical/emulator end-to-end validation and full locale translation before full acceptance. Retain Phase 02 data-rights/coverage blockers and Phase 03 candidate-ranking limitations. Record the unresolved upstream Expo CLI/Zod advisory; do not force an incompatible SDK downgrade or claim a clean security audit. No Phase 05 work is authorized by these client interfaces.
