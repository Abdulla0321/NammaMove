# Phase 02 ? Bengaluru transit data

Status: Planned; not implemented.

## Prerequisites
Phase 01 storage; documented permission and provenance for each source.

## Implementation tasks
- [ ] Build versioned GTFS ingestion for stops, routes, trips, stop times, calendars, exceptions, shapes and transfers
- [ ] Normalize Asia/Kolkata dates, overnight times above 24:00 and stable source IDs
- [ ] Record licenses, retrieval time, checksums, coverage and quality; quarantine invalid data
- [ ] Define GTFS-Realtime adapter contracts and recorded fixtures; keep freshness separate from service state
- [ ] Promote snapshots atomically with last-known-good rollback

## Expected deliverables
Authorized source register, import CLI/jobs, validated dataset and feed quality report.

## Edge cases
Unavailable licensed feed; malformed ZIP; missing optional tables; duplicate IDs; holiday service; overnight trip; partial snapshot; future timestamp.

## Automated tests
Licensed or synthetic fixtures for calendar exceptions, overnight ordering, duplicates, quarantine, atomic promotion and stale-age boundaries.

## Completion criteria
Authorized imports are repeatable; bad snapshots never replace good data; coverage and provenance are visible; samples remain labeled.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
