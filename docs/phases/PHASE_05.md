# Phase 05 ? Live tracking and feed reliability

Status: Planned; not implemented.

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
