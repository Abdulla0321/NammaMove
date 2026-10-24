# Phase 04 ? Mobile UI and web shell

Status: Planned; not implemented.

## Prerequisites
Phase 03 stable API contracts; Phase 01 identity.

## Implementation tasks
- [ ] Introduce Expo/React Native and React operations shell with strict TypeScript
- [ ] Implement stop search, preferences, map/list alternatives and plain-language confidence notices
- [ ] Add active itinerary, favorites, timestamped offline cache and manual origin when permission denied
- [ ] Support screen readers, large text and English/Kannada/Hindi translation structure
- [ ] Add client lint/format/type checks, component tests and build validation to CI when clients exist

## Expected deliverables
Runnable Expo app, React web shell, generated API contracts and client quality gates.

## Edge cases
Location denied; offline launch; slow network; large fonts; small screens; missing fare; language fallback; no accessible route.

## Automated tests
Component search/loading/error/offline tests; API contracts; accessibility assertions; emulator/device end-to-end journey selection.

## Completion criteria
Documented device startup works; riders can select truthful feasible journeys with offline and permission-denial paths.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
