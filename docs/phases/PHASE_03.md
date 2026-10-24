# Phase 03 ? Multimodal routing

Status: Planned; not implemented.

## Prerequisites
Phase 02 validated GTFS/OSM inputs and agreed OTP resource budget.

## Implementation tasks
- [ ] Introduce OpenTripPlanner behind a typed adapter and versioned graph build pipeline
- [ ] Support transit/walking transfers, timetable feasibility, accessibility, walking limits and fare availability
- [ ] Normalize itinerary contracts with timestamps, sources and uncertainty
- [ ] Separate physical ETA from generalized ranking penalties; retain explicit simulator fixtures
- [ ] Bound query work, timeouts and graph fallback; explain no-route states

## Expected deliverables
OTP build pipeline, routing adapter, versioned journey contract and integration fixtures.

## Edge cases
Missed last service; inaccessible lift; disconnected graph; same/unknown stop; zero walking tolerance; OTP outage; missing fare.

## Automated tests
OTP recorded contracts; calendar/transfer integration; directed/accessibility constraints; timeouts; rollback and bounded-load benchmarks.

## Completion criteria
Fixture journeys are feasible; ETA excludes artificial penalties; p95 target under 2 seconds at declared pilot load; outages degrade clearly.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
