# Phase 05 - Live tracking and feed reliability

## Updated product dependency (2026-11-14; planned, not implemented)

After ingestion durability/provenance, establish owner-scoped JourneySession/JourneyLeg and revision contracts plus authenticated scoped mobile journey progress, reconnect/polling, consent and low-battery behavior. Preserve existing saved-history/routing contracts; GPS is never check-in/out or completion proof. Ticket issuance, wallet eligibility/holds, QR dual validation, debit and settlement are Phase 08. Phase 06 safe recovery consumes progress foundations only after its gates. See [PRD v1.1](../PRD.md) and [architecture](../ARCHITECTURE.md#updated-journey-wallet-and-validation-design--planned). These additions do not mark Phase 05 accepted.

Status: In progress, synthetic replay/adapters, Redis whole-feed ingestion and owner-run durability/retention/restart watermarks (2026-11-15). Deferred Phase 04 and real-source gates remain open; no live provider activation or full Phase 05 acceptance. See [realtime](../REALTIME.md) and [durability scope](../DURABLE_INGESTION.md).

## Prerequisites
Phases 02/04 accepted; authorized realtime feeds; consent and retention policy.

## Implementation tasks
- [ ] Implement GTFS-RT vehicle, trip-update and alert ingestion with independent freshness/service state machines
- [ ] Introduce Redis ephemeral caching, bounded queues and idempotent workers while evidence stays durable
- [ ] Quarantine impossible positions and handle duplicate/out-of-order event time
- [ ] Deliver authenticated scoped WebSocket/push updates with reconnect and polling fallback
- [ ] Expose observed age, ETA uncertainty, opt-in tracking and low-battery behavior

## Expected deliverables
Feed workers, live delivery, consent controls and feed-quality metrics.

## Edge cases
Feed blackout; skewed clock; duplicate/reordered event; spoofed GPS jump; vehicle reassignment; expired token; app backgrounding.

## Automated tests
Recorded GTFS-RT replay; missing GPS never cancels; independent cancellation does; event-order/idempotency tests; socket authorization/reconnect; retention deletion.

## Completion criteria
Pilot freshness is measured; replay is stable; no cancellation derives from missing telemetry; subscriptions and location access are authorized.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.


## First engineering slice - 2026-11-03
Implemented typed synthetic event/replay models, independent observation-age/freshness/service evidence, ordered/idempotent bounded state, conflicting-ID/clock rejection, same-vehicle GPS-jump quarantine, reassignment handling and retention. Eighteen focused tests pass. No protobuf decoder, Redis worker, durable ingestion, WebSocket/push API or mobile tracking is claimed. Existing implementation checkboxes above remain incomplete. See [evidence](../evidence/phase05-foundation-2026-11-03.json).

## Bounded adapter slice - 2026-11-04
Added synthetic-only GTFS-RT 2.0 FULL_DATASET protobuf normalization for explicit vehicle observations, trip-level scheduled/delay/cancellation evidence and advisory trip-targeted alerts. Sealed authored fixture provenance; byte/entity/fanout/text bounds, clock/static-trip checks and atomic rejection paths are tested with the actual binding. Missing entities/GPS and NO_SERVICE alerts never generate cancellation. This is a conservative subset, not a complete GTFS-RT validator or snapshot-replacement worker. Stop-level uncertainty, differential/deletion semantics, production provenance, Redis/durable workers, authenticated delivery and consent/battery controls remain incomplete; checkboxes stay open. See [adapter evidence](../evidence/phase05-adapters-2026-11-04.json).

## Atomic Redis event-state slice - 2026-11-04
Implemented bounded WATCH/MULTI/EXEC event-state updates for concurrent synthetic workers, independent payload TTLs and receipt-retained ordering/dedup guards. Timestamped channel snapshots expose freshness, observation/receipt times, synthetic observed positions, uncertain delay predictions and unloaded static schedules separately. Missing/stale GPS never cancels service; stale independent service evidence becomes unknown. Redis errors/corruption fail closed, ambiguous commits can be retried idempotently, and real disposable-server restart recovery was exercised. See [Redis evidence](../evidence/phase05-redis-2026-11-04.json).

The Redis/worker checkbox remains incomplete: no whole-feed FULL_DATASET replacement/withdrawal, alert interval scheduler, bounded background queue or durable evidence worker is implemented. Next implement those ingestion-worker boundaries before any authenticated delivery. Source rights/static-snapshot binding, privacy/retention approval, Redis production security/availability, Phase 02 real-data and deferred Phase 04 acceptance remain open. No live feeds, production activation, automatic rerouting or Phase 06 work.

## Bounded whole-feed ingestion slice - 2026-11-12

Supersedes the preceding whole-feed/queue implementation gap for synthetic scope only. Added atomic FULL_DATASET replacement/empty-feed omission withdrawal, header ordering/exact fixture-version matching, future/disjoint/open alert intervals with read-time expiry and final-end TTL, and an explicit byte/job-bounded local queue with backpressure and bounded deterministic retry. Generation integrity, retained order/receipt guards and conservative same-vehicle gap quarantine prevent partial evidence, false duplicate success, freshness renewal or GPS-check bypass. Omission and feed failure never infer service cancellation/recovery. Existing APIs, Auth, migrations, database schema and mobile code remain unchanged; simulation labels remain mandatory.

Baseline 79 replay/adapter/state cases passed before implementation. Final **263 backend tests passed / zero failed / zero skipped**, including 49 new ingestion cases, genuine Redis/PostGIS/Auth/OTP and actual disposable Redis outage/restart verification. Ruff lint/format, strict mypy and dependency consistency pass. See [ingestion evidence](../evidence/phase05-ingestion-2026-11-12.json).

The phase checkboxes remain incomplete: the queue is process-local/explicitly driven, not durable or production fetch orchestration. Next: durable evidence/retention and restart watermark policy via reviewed migrations, plus trusted source/immutable static-snapshot binding. Source rights, Redis production security/availability, privacy, deferred Phase 04 and Phase 02 gates remain open. Do not start authenticated mobile delivery or Phase 06 yet.

## Integrity/retry follow-up - 2026-11-14

Preserved existing whole-feed work, adding per-record normalized-event fingerprints and identity/expiry/scope/receipt/order-guard validation. Valid-JSON corruption fails unavailable/unknown instead of exposing changed cancellation/GPS evidence or acknowledging a false duplicate. Unexpected ordinary processing exceptions now use the finite retry budget and release reserved capacity on exhaustion, with sanitized counters only. Old `full-v1` manifests fail closed under the explicit `full-v2` fixture policy; no automatic reset or migration.

Reverified 128 existing realtime cases; added 13 follow-up cases. Final focused ingestion **62 passed / 0 failed / 0 skipped**; full backend **276 passed / 0 failed / 0 skipped**, including genuine Redis/PostGIS/Auth/OTP. Actual isolated Redis restart and Ruff/format/mypy/pip checks pass. See [follow-up evidence](../evidence/phase05-followup-2026-11-14.json) and ADR-028. Next remains durable ingestion evidence/retention/restart watermarks and trusted source/static-snapshot binding; no session schema, delivery, QR/wallet or Phase 06 code is introduced.

## Phase 05-D - 2026-11-15

Owner-run synthetic source/static-snapshot registration, idempotent accepted/rejected generation metadata, original-deadline latest checkpoint, durable header/receipt/order-guard watermarks and explicit dry-run-first retention now wrap the existing ingestion/cache. PostgreSQL source locks and integrity/static/audit validation gate every Redis recovery/read; SQL failures and ambiguous commits never become unverified cache success. Migration 0003 adds two private RLS-protected tables only; earlier API compatibility is retained. No persistent application/Auth migrations or new credentials.

**309 backend passed / 0 failed / 0 skipped**, including 33 durable cases, genuine PostGIS/Redis/Auth/OTP, upgrade/downgrade/DDL rollback, concurrency, retention, corruption/mismatch, SQL/Redis failures and actual isolated Redis restart recovery. Existing 62 Phase 05-C cases were independently reverified. Ruff lint/format, strict mypy and pip consistency pass. See [evidence](../evidence/phase05-durable-2026-11-15.json), ADR-029 and [runbook](../DURABLE_INGESTION.md).

The worker remains explicit maintenance-owner synthetic code. Next accept a dedicated non-owner worker identity/catalog-RLS/provisioning path and scheduled bounded retention/recovery, then durable dispatch/fetch orchestration. Production rights/privacy/Redis security/failover, authenticated delivery, active journeys and full phase acceptance remain gated. No wallet/QR/payments or Phase 06 implementation.
