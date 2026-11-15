# Phase 05 synthetic replay foundation

## Scope
Phase 05 work begins following the user's 2026-11-03 request to proceed with deferred Phase 04 gates. This is local synthetic engineering only. Phase 02 provider rights/coverage, deferred Phase 04 security/CI/lifecycle gates and authorized realtime-feed prerequisites remain unresolved. No existing endpoint, native app, graph or deployed service is changed.

The foundation is `backend/app/realtime/replay.py`, a normalized event model and single-process deterministic fixture harness. The second slice, `backend/app/realtime/gtfs_rt.py`, decodes a bounded, synthetic-only protobuf subset into those events. The third slice, `backend/app/realtime/redis_state.py`, supplies atomic Redis event-state updates and timestamped read snapshots for concurrent synthetic workers. The fourth slice, `backend/app/realtime/ingestion.py`, adds whole-feed replacement and an explicitly driven bounded local queue. These isolated primitives are not a production worker or live tracking implementation. The [GTFS-Realtime reference](https://gtfs.org/documentation/realtime/reference/) distinguishes vehicle positions, trip updates and alerts; these evidence channels remain independent.

## Implemented behavior
- Every event/output is labeled simulation; arbitrary extra fields, live labels, naive clocks and invalid/non-finite coordinates are rejected.
- Source/trip/service-date/channel isolation; fixture source allowlist is constructor configuration, never a client verification flag.
- Independent observation ages/freshness; fresh GPS/alerts do not refresh service evidence. Missing/stale GPS never implies cancellation. Only fresh explicit independent fixture trip updates may report cancellation; no graph edge is ever closed. Stale service evidence becomes unknown and ETA remains uncertain.
- Event-ID deduplication, conflicting-ID rejection, strict per-channel observation ordering, future/expired event quarantine and monotonic receipt clock checks.
- Same-vehicle impossible-speed quarantine with a configurable illustrative bound; reassignment does not compare different vehicles. This is not proof that an accepted position is genuine.
- Bounded last-observation/dedup state, observation-time retention and raw-free outcome counters. Quarantine retains no payload/history. Capacity rejects additional events rather than evicting active ordering/dedup protection.

## Validation
Run from repository root with the existing venv:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider backend/tests/test_realtime_replay.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
```

The foundation tests use independently authored inline fixtures, not recorded licensed provider feeds. Adapter tests roundtrip a sealed authored JSON fixture through the actual protobuf binding; they establish only the supported subset, not full protobuf/GTFS-RT conformance, pilot freshness or durable/Redis evidence. Outcome counters are local diagnostics, not production feed-quality telemetry.

## Bounded protobuf adapter - 2026-11-04
`FixtureGtfsRtAdapter` has no network access or API integration. Constructor configuration identifies one synthetic source and at most 1,000 authored trip/service-date pairs; it does not authorize a provider or bind to the production static catalog. The pinned `gtfs-realtime-bindings==2.0.0` wire schema deliberately excludes newer GTFS-RT extensions; unknown wire fields are rejected. Protobuf is introduced in its scheduled Phase 05 scope; dependency consistency and runtime checks do not constitute security approval.

- Accept only version 2.0 FULL_DATASET envelopes. Reject DIFFERENTIAL and deletion flags (even explicit false), duplicate entity IDs and multi-channel entities atomically. Missing entities produce no new evidence, not cancellation or recovery. This is stateless normalization, **not FULL_DATASET cache-replacement semantics**; a future worker must implement replacement/withdrawal separately before delivery.
- Default payload cap is 256 KiB, configurable up to 1 MiB; at most 1,000 entities/events, 16 selectors per alert, 32 active periods, eight translations per text and 2,000 characters per translation. Reject before returning any events; errors contain no feed identifiers or raw provider text.
- Require bounded aware receipt/header/observation clocks. Header refresh never rewrites vehicle/trip observation timestamps. Event identity includes normalized entity content and observation identity, allowing stable GTFS entity IDs to carry later updates while duplicate observations retain their age.
- Vehicles require explicit vehicle identity, coordinates, trip/date and observation timestamp. Replaying normalized events preserves GPS-jump quarantine, reassignment, ordering and deduplication behavior.
- Trip updates support only SCHEDULED and explicit CANCELED relationships and optional bounded trip-level delay. Missing delay does not mean on-time certainty. Stop-level predictions/uncertainty, frequency trips, additions/replacements and unsupported fields reject the feed; no guessed ETA is emitted.
- Alerts require exact authored trip/date selectors; broad route/agency/stop selectors are unsupported. Active intervals are checked at decode time. Alert timestamps indicate **feed publication**, not incident observation or verification. Even NO_SERVICE alerts remain advisory and cannot change service status. Alert text is validated but not retained in normalized events. Future workers must enforce interval-end expiry as well as TTL; this harness does not implement scheduled alert withdrawal.

Fixtures live in `backend/tests/fixtures/realtime/`. `manifest.json` records independent synthetic provenance and SHA-256 of canonical JSON (`sort_keys=True`, separators `(',', ':')`), independent of checkout line endings. Tests fail if the authored fixture changes without a reviewed seal update. No provider data, device location history or binary feed is committed.

Run the adapter and foundation tests together:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider backend/tests/test_realtime_gtfs_rt.py backend/tests/test_realtime_replay.py
```

See [adapter evidence](evidence/phase05-adapters-2026-11-04.json) for actual checks and retained acceptance limits.

## Atomic Redis tracking-state slice - 2026-11-04
`RedisTrackingState` accepts normalized synthetic events only. Nothing starts at API boot; no existing API, authentication, routing, mobile behavior or database schema is changed. Configure exact source/trip/date scope and a `nammamove:simulation:<name>` namespace in owner code. Use `tracking_client` to create connections with 250 ms connect/socket timeouts, no hidden connection retries and a bounded pool. Custom clients must supply finite timeouts no greater than one second and zero hidden retries.

- One source metadata key serializes writers with WATCH/MULTI/EXEC; each transaction atomically commits ordering/dedup guards and the changed channel snapshot. Keys share a Redis Cluster hash tag, although cluster/failover behavior has not been exercised. Contention is retried at most eight times by default (configurable 1-16); then `contended` is returned. No unbounded internal work queue exists.
- Separate vehicle/trip/alert payload keys hold only the latest observation, with TTL based on remaining observation retention, not a new full lifetime for delayed receipt. Metadata contains hashed event fingerprints/identities and ordering timestamps, not position history. Guards survive payload expiration for up to the configured receipt retention; duplicate reads/ingestion do not extend TTL. Active guard/dedup capacity defaults to 1,000, cannot exceed 1,000, and serialized metadata is capped at 512 KiB. `capacity` rejects instead of evicting protection.
- Freshness defaults to fresh at ages <=90 seconds, stale at ages >90 and <900, unavailable at >=900 or missing. Both thresholds are configurable with `0 < fresh < retention <=900`. Reads recompute ages using the supplied aware UTC-compatible clock and do not renew storage. Returned channels expose observed timestamp, received timestamp and observed age separately. Receipt-clock regression or mixed worker policies fail closed; workers need synchronized clocks.
- `data_mode=simulation` remains mandatory. `observed_position` is available only for fresh vehicle evidence. `predicted` contains only a separately labeled synthetic trip-update delay with ETA uncertainty, never a fabricated arrival time; cancelled/unknown service does not expose delay predictions. `scheduled_information=not_loaded` makes clear that this cache does not load static timetables. A trip-update SCHEDULED relationship is not proof of on-time operation.
- Missing GPS, feed silence, missing payloads, advisory alerts and stale service evidence never generate confirmed cancellation. Fresh independent trip-update cancellation remains separate from GPS. There is no feed-fetcher or feed-health monitor: observation silence means lack of evidence, not proof a provider or vehicle stopped operating.
- Redis errors, malformed/mismatched state and missing metadata with surviving payloads return unavailable storage with unknown service and no position/prediction. No stale local cache or false ingestion success substitutes for Redis. A lost EXEC response returns `unavailable`; replay resolves to `duplicate` if the write committed. Reconnection with intact state retains guards. A nonpersistent Redis restart loses ephemeral guards/state: snapshots become unknown until admissible independent evidence arrives. There is no durable exactly-once or failover guarantee; replay older than retention cannot resurrect evidence.
- Same-vehicle speed quarantine and vehicle reassignment remain enforced inside the transaction. All rejections return bounded outcome names and contain no connection URL, token, raw feed text or coordinates in errors.

### Real Redis verification
Use a **dedicated disposable local Redis**, not an existing application cache. The tested instance is `redis:7-alpine` (server 7.4.12), loopback port 16379, no RDB/AOF, no volume, 32 MiB, `noeviction`. Do not enable persistence for these synthetic position payloads or reuse these commands on a production service. No credentials/ACLs were created or changed.

```powershell
# Create only if this dedicated test container does not already exist.
docker run --detach --name nammamove-phase05-redis-test --publish 127.0.0.1:16379:6379 redis:7-alpine redis-server --save "" --appendonly no --maxmemory 32mb --maxmemory-policy noeviction
# On later runs, start the existing dedicated test container instead.
# docker start nammamove-phase05-redis-test
$env:NAMMAMOVE_TEST_REDIS_URL = 'redis://127.0.0.1:16379/0'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider backend/tests/test_realtime_redis.py
# After tests, stop only this disposable instance.
docker stop nammamove-phase05-redis-test
```

Tests use unique namespaces and delete only their own keys; never FLUSHDB/FLUSHALL. Missing test configuration produces explicit skips, not acceptance. Tests exercise real transactions, concurrent barriers, exact logical freshness/retention boundaries, natural server TTL deletion, capacity, policy mismatch, corruption, replay and GPS quarantine. Fault injection after a real committed EXEC verifies ambiguous responses. A separate actual stop/restart of this task's disposable server verifies real connection loss and cold-cache recovery; it is not a production failover drill. See [Redis evidence](evidence/phase05-redis-2026-11-04.json).

## Whole-feed ingestion slice - 2026-11-12

`RedisFullDataset(adapter, state, expected_feed_version=None)` uses constructor-owned synthetic scope and separate `full:` keys in the same source hash slot. It does not write legacy event-state keys. `ingest(payload, now=...)` accepts bounded authored protobuf bytes, not client-provided normalized batches or authorization flags. Nothing starts automatically at API startup, and no feed URL is fetched.

- Validate the entire feed before mutation. The manifest, generation-specific payload keys and omission deletions commit in one WATCH/MULTI/EXEC. Readers validate the entire referenced generation before returning any trip; missing unexpired/corrupt payloads fail closed. Duplicate acknowledgement also validates generation integrity. Invalid, oversized, conflicting, quarantined and out-of-order feeds leave the prior valid generation untouched. Redis runtime/connection failures are unavailable, never success or a rollback guarantee; a corrupt/incomplete generation requires operator investigation, not silent repair.
- A successful FULL_DATASET replaces all preceding observations for this configured source, including an empty snapshot. Omitted vehicle/trip/alert payloads are deleted. Withdrawing cancellation evidence means unknown, not confirmed scheduled service or recovery. Missing GPS never cancels service. A failed feed is not an empty successful feed.
- Strictly increasing header timestamps order snapshots. Equal timestamp plus canonical content is duplicate; different content is conflict, and older headers reject. Entity order alone does not change identity. Observation timestamps retain independent ordering guards across omissions. Refreshed headers cannot refresh GPS/trip evidence or original receipt time. Guards contain hashes/timestamps, not GPS history, and expire within the configured retention. Where omission removes a same-vehicle position comparison baseline, newer positioned observations are conservatively quarantined until guard expiry or explicit reassignment; an omission cannot bypass jump checks.
- `feed_version` is an opaque static-feed identifier, **not** a sortable snapshot sequence. Exact constructor match is required (including absence by default); no in-place static-version switch is allowed. The pinned `gtfs-realtime-bindings==2.0.0` lacks this standard header field. A private protobuf descriptor pool adds only the official optional string `FeedHeader.feed_version` at wire field 4, without changing dependencies or global descriptors. All other unknown fields still reject. This fixture version check is not production static-snapshot/provenance authorization.
- Independent observation TTLs physically remove GPS/trip payloads; reads cannot renew them. The manifest has bounded receipt retention, so header guards survive expired payloads but not Redis loss. Multiple advisory alerts may coexist. Future intervals are retained, activation is start-inclusive, expiry end-exclusive, and disjoint gaps are inactive. Reads evaluate intervals without requiring a running scheduler; payload TTL is capped at the final interval end (or observation retention for open ends). No alert can cancel service or verify an incident.
- `FeedSnapshot` exposes simulated feed freshness separately from nested tracking-channel freshness/service. All returned snapshots and worker results retain simulation labels. No public API, Auth, database migration, routing graph or mobile contract changes.

### Queue, retries and recovery

`FullDatasetWorker(store)` is an explicitly tick-driven in-process queue; owners call `submit(payload, now=...)` and `run_one(now=...)`. It creates no autonomous thread, poller or network fetcher. Defaults: 8 outstanding jobs, 2 MiB total bytes and 3 processing attempts. Hard limits: 64 jobs, 8 MiB and 5 attempts. The adapter byte cap applies before admission. Capacity includes in-flight and retry work; saturation returns backpressure without evicting older work. Producers must retain/resubmit rejected work rather than assuming acceptance. One local consumer processes at a time; independently configured processes serialize whole-feed commits through Redis.

Only unavailable/contended outcomes retry. Due times use deterministic delays of 1, 2, 4 and 8 seconds, with no internal sleep. Invalid/outdated/conflicting feeds terminate without retry. Expired queued bytes reject on processing. Exhausted retries release the bounded slot and increment an outcome counter; no raw feed/dead-letter history is retained. Lost EXEC responses retry by header/content identity and acknowledge only intact duplicate generations.

Worker reconstruction loses the local queue; the producer must resubmit. Reconnection to intact Redis preserves ordering. Nonpersistent Redis restart loses ephemeral observations/guards: snapshots are unknown until admissible independent synthetic evidence is supplied. There is no durable enqueue/ack, cross-process queue, exactly-once, durable watermark or crash-survival guarantee; durable evidence/recovery is the next slice, not a hidden acceptance claim.

### Executed verification

Before implementation: 79 existing replay/adapter/state tests passed, zero skipped, including 28 existing Redis-state cases. Final suite: **263 backend tests passed, zero failures/skips**, including **49 new ingestion tests**, real Redis, new disposable PostGIS, genuine existing Supabase Auth and sealed synthetic OTP. Ruff lint/format, strict mypy (32 app files), pip consistency and whitespace checks pass. Existing Starlette HTTPX deprecation and Alembic geography-reflection warnings remain.

Tests cover whole-feed/empty replacement, safe omission, ordering/version matching, duplicates/conflicts, failed-feed preservation, independent ages, future/disjoint/open alert ranges, natural server TTL, inactive fanout, capacity, GPS gaps/reassignment, concurrent snapshot writers/readers, real WATCH races, ambiguous commits, corrupt/incomplete state, byte/job/in-flight backpressure and bounded retry exhaustion. An actual ID-checked stop/start of the newly created loopback-only nonpersistent Redis instance verified unavailable/unknown outage behavior, retained queued retry capacity, unknown cold cache, successful retry, worker reconstruction/resubmission deduplication and expired replay rejection. This is not production failover evidence.

```powershell
# Dedicated disposable Redis only; do not point tests at an application cache.
$env:NAMMAMOVE_TEST_REDIS_URL = 'redis://127.0.0.1:16380/0'
.\.venv\Scripts\python.exe -m pytest -q backend/tests/test_realtime_ingestion.py backend/tests/test_realtime_redis.py backend/tests/test_realtime_gtfs_rt.py backend/tests/test_realtime_replay.py
```

See [ingestion evidence](evidence/phase05-ingestion-2026-11-12.json). Historical slice descriptions above retain their original scope; this section supersedes their future-worker limitations only for the implemented synthetic boundaries.

## Ingestion integrity/retry follow-up - 2026-11-14

The existing whole-feed slice was retained rather than duplicated. Each record now pins a normalized event fingerprint. Reads and duplicate acknowledgements reconstruct record identity/expiry and validate payload scope and receipt chronology, so syntactically valid corruption cannot present changed service, GPS, trip or identity as valid evidence. Duplicate/unknown-scope manifest records also fail closed. These hashes detect inconsistency, not malicious rewriting of both manifest and payload by a privileged Redis administrator; production Redis trust/security remains gated.

The ephemeral policy is now `full-v2`. Old-policy manifests reject as unavailable rather than being silently interpreted or deleted. Stop local fixture writers and allow old keys to expire within configured retention, or use a new isolated fixture namespace; there is no production deployment or automatic reset/migration. Existing public API and event-state contracts remain unchanged.

Unexpected ordinary processing exceptions become sanitized unavailable outcomes, increment `worker_error` and follow existing bounded retries. The removed in-flight job keeps its reserved slot/bytes during retry, then releases them on terminal exhaustion. A post-commit exception safely retries to an intact duplicate. This prevents stranded slots; it does not make the process-local queue durable or recover a process crash/forced interruption. No raw error message, provider data or coordinates enter counters/results.

Updated product requirements are planning-only: Phase 05 later establishes owner-scoped JourneySession/JourneyLeg and authenticated progress foundations, Phase 06 safe confirmed synthetic fare-aware recovery, Phase 07 uncertain predictions, Phase 08 wallet/QR/booking/financial orchestration, Phase 09 disputes/reconciliation/digital twin, and Phase 10 approved integrations/pilot. See [PRD](PRD.md), [architecture](ARCHITECTURE.md#updated-journey-wallet-and-validation-design--planned) and ADR-027/028. This follow-up implements none of those financial/progress/delivery features. Fresh verification is recorded in [follow-up evidence](evidence/phase05-followup-2026-11-14.json).

## Phase 05-D durable ingestion (2026-11-15)

`app.realtime.durable.DurableIngestion` wraps the existing whole-feed cache and plugs into `FullDatasetWorker` without a second normalization engine. Explicit maintenance-owner registration pins a validated synthetic static dataset, checksum/manifest/version, trip/date/calendar facts and cache policy/namespace. Optional route/direction references must match that snapshot. Two additive private RLS-protected tables persist bounded idempotent outcome metadata and a latest recovery checkpoint/watermark; no raw feeds or GPS history are archived. Separate omission-guard commitments and unexpired acceptance evidence are checked before recovery. No roles/credentials are created by migrations.

Accepted generation persistence requires a successful SQL commit. Redis changes before that are provisional; all durability-gated reads/retries serialize through the source lock and rebuild from the committed checkpoint. A failed SQL write cannot become visible as accepted state through this gate, and an ambiguous committed response retries as duplicate. Observation/alert deadlines and original receipt times survive recovery, with missing/expired GPS still unknown rather than cancelled. Explicit owner retention is dry-run by default, removes expired metadata/checkpoint payloads and preserves restart watermarks/guard digests. It is not a scheduled or production retention service. See [migration effects, ownership, failure semantics and retention](DURABLE_INGESTION.md).

The old ephemeral cache remains compatible; durable sources require their own exclusive namespaces and must not expose standalone cache reads/writes. API readiness supports 0002/0003 because the worker schema is additive; no persistent database upgrade was performed for this task. This slice is owner-run local synthetic engineering, not a non-owner production worker, live feed activation or Phase 05 acceptance.

## Remaining Phase 05 slices and completion gates

Next implement/test dedicated non-owner worker identity and catalog-RLS/provisioning acceptance, scheduled bounded retention and recovery operation, then durable dispatch/fetch orchestration. Distributed queue/ack, broader GTFS-RT support, real provider rights/provenance, Redis ACL/TLS/security/failover and consent/battery controls remain incomplete. Phase 02 real-data and deferred Phase 04 gates remain open. Authenticated delivery, active journey foundations and Phase 06 are not started. No wallet/QR/payment execution, graph mutation, automatic rerouting, production activation or credential change is introduced. Full acceptance still requires the original completion criteria and privacy/source prerequisites.
