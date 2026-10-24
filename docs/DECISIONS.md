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
