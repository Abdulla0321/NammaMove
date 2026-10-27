# Phase 04 - Commuter mobile application and web shell

Status: implementation and local automated integration verified; full device/localization/security acceptance remains pending. This phase uses the explicitly authorized synthetic network. Real Bengaluru data blockers remain open. No Phase 05 functionality or deployment is enabled.

## Prerequisites
- [x] Phase 03 merged routing contract and genuine local Phase 01 Auth.
- [x] Existing monorepo, Expo SDK 55 / React Native / React web and strict TypeScript; no nested Git repository.
- [ ] Verified official real-provider coverage is still blocked; synthetic-only development does not close Phase 02 gates.

## Implementation tasks and deliverables
- [x] Android-first responsive Expo commuter app and shared React web preview/read-only service-status shell.
- [x] Onboarding, Supabase sign-in/signup confirmation notice, verified bearer API integration, one refresh/retry, session-expiry handling and explicit sign-out.
- [x] Search/select authored stops, consented foreground nearby lookup, manual origin, date/time/arrival/departure, mode/walking/accessibility constraints and preferences.
- [x] Alternatives with source fares/unknown fares, time/walk/transfers, initial waiting, bounded-ranking explanations, detail legs, geographic endpoints and optional native basemap.
- [x] Per-user native-encrypted favorites/recent searches and consented timestamped 24-hour offline journey cache; clear-data controls; web memory-only storage.
- [x] English plus Kannada/Hindi typed dictionaries with English fallback, screen-reader names/states, announcements, scrollable large-text layouts, skeletons, empty/error states and Android Back navigation.
- [x] Generated backend OpenAPI routing types, runtime response validation, exact opt-in browser CORS and client quality/build CI configuration.
- [x] Synthetic/approximate/scheduled/unavailable/stale labels; no live positions, disruption closures or recovery workers.

Deliverables: [mobile workspace](../../apps/mobile/), [Windows/manual runbook](../MOBILE.md), [aggregate evidence](../evidence/phase04-mobile.json), generated contracts, behavioral/component tests and CI checks. The web shell is a shared commuter preview with read-only health status, not an operations administration feature from Phase 09.

## Edge cases and automated tests
Tests cover onboarding/confirmation, destination selection, invalid timezone/time, permission denial/manual origin, skeleton/duplicate-call prevention, offline/unavailable provider, no-route, rejected token refresh, unknown fares, malformed/live-labeled responses, cache corruption/consent/expiry/user isolation, failed encrypted writes, Unicode/large session values, explicit sign-out data removal and redundant token-refresh events. Component accessibility/control checks run at 320 and 800 widths with 200% font scale; they do not simulate Android's real layout engine or establish TalkBack certification.

The real TypeScript integration script calls genuine local Supabase and the existing non-owner FastAPI/OTP runtime: health, four preferences, bus-only, impossible journey and invalid-token rejection. It requires opt-in local configuration and fails without services; native-module mocks do not substitute for that evidence. Existing backend real PostGIS, Auth and OTP regression tests remain enabled.

## Completion criteria and acceptance evidence
| Criterion | Actual local result |
|---|---|
| Select truthful feasible journeys | Actual TypeScript/Auth/API/OTP checks passed on independently authored fixture, with 30/50-INR alternatives and a 20-INR bus-only journey |
| Offline and permission denial | Behavioral/component tests passed; native persistence/permission prompt lifecycle still requires a device |
| Unit/component contracts and quality | Latest exact counts and command outcomes in [phase status](../PHASE_STATUS.md) and evidence |
| Web and Android build validation | Expo web and Hermes Android JavaScript exports passed; this is not an APK/AAB, install or emulator run |
| Documented device startup works | Commands documented; no Android SDK/adb/emulator available locally, so not yet verified |
| Accessible/localized product acceptance | Labels and responsive component cases implemented/tested; TalkBack, actual font layouts and full Kannada/Hindi translation remain open |
| Release readiness | Not met: native/device evidence, dependency security resolution, hosted CI and external data gates remain open |

**Do not claim full Phase 04 acceptance.** Engineering implementation, automated fixture integration and bundle exports are verified; the documented device-startup/end-to-end gate is unresolved. No new database migration is needed. No commit, push or merge is performed.

## Remaining limitations and next verification
Follow the exact emulator/USB startup and manual checklist in [MOBILE.md](../MOBILE.md). Verify secure storage/relaunch/sign-out/backup behavior, TalkBack, Android Back/keyboard/rotation and Google Maps key restrictions on a real build. Complete language translation and review source data before real routing. Offline records require a restorable local identity; unavailable/expired Auth can require reconnecting. Review Expo CLI's transitive Zod advisory rather than forcing a breaking SDK downgrade. A browser automation surface was unavailable here, so visual browser QA is also pending. Signup email/deep-link delivery is provider-dependent and unverified. Future live/disruption fields remain inactive.

## Safety gate
Missing GPS means uncertainty, never cancellation. Simulation remains visible on every journey screen. Cache is stale historical information, never a silent current recommendation. Native map lines are approximate endpoint links, not validated paths. Real lift accessibility and congestion-safe rerouting are not claimed. Do not start Phase 05.
