# Phase 05 - Live tracking and feed reliability

Status: In progress, synthetic replay, bounded protobuf adapters and atomic Redis event-state primitives (2026-11-04). The user requested Phase 05 work while deferring Phase 04 acceptance follow-ups. This does not accept those gates or authorize live provider activation. See [realtime scope/runbook](../REALTIME.md).

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
