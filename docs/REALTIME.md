# Phase 05 synthetic replay foundation

## Scope
Phase 05 work begins following the user's 2026-11-03 request to proceed with deferred Phase 04 gates. This is local synthetic engineering only. Phase 02 provider rights/coverage, deferred Phase 04 security/CI/lifecycle gates and authorized realtime-feed prerequisites remain unresolved. No existing endpoint, native app, graph or deployed service is changed.

The foundation is `backend/app/realtime/replay.py`, a normalized event model and single-process deterministic fixture harness. The second slice, `backend/app/realtime/gtfs_rt.py`, decodes a bounded, synthetic-only protobuf subset into those events. The third slice, `backend/app/realtime/redis_state.py`, supplies atomic Redis event-state updates and timestamped read snapshots for concurrent synthetic workers. These isolated primitives are not a production worker or live tracking implementation. The [GTFS-Realtime reference](https://gtfs.org/documentation/realtime/reference/) distinguishes vehicle positions, trip updates and alerts; these evidence channels remain independent.

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

## Next slices and completion gates
Next implement a bounded FULL_DATASET ingestion worker: feed-version/header ordering, atomic snapshot replacement/omission withdrawal, alert active-period expiry, bounded queue/backpressure and retry/recovery policy with genuine Redis tests. Event-state transactions here are **not whole-feed snapshot commits**. Production owner-configured feed trust/provenance and static-snapshot matching, broader GTFS-RT support, durable evidence/retention via reviewed migrations, Redis ACL/TLS/availability review and device consent/battery controls remain incomplete. Authenticated delivery and Phase 06 are explicitly unstarted. Preserve existing API contracts and simulation labels. No automatic rerouting, production activation, credential changes or live source downloads are authorized. Full phase acceptance requires the original phase completion criteria and source/privacy prerequisites.
