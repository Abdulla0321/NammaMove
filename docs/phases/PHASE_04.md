# Phase 04 - Commuter mobile application and web shell

Status: 2026-11-03 automated synthetic checks (52 mobile, 135 backend, 11 real-client checks) and main user-reported custom Android walkthrough pass. APK/install/Maps, storage/relaunch/backend-loss, sign-out/clearing, permissions, navigation, TalkBack/layout and both language reviews are recorded. Full acceptance remains pending security, hosted CI and remaining lifecycle/expiry/backup/email gates. See [current evidence](../evidence/phase04-resume-2026-11-03.json). Real Bengaluru data blockers remain open; Phase 05 stays unstarted.

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
| Select truthful feasible journeys | 11 current actual-client checks pass against genuine Auth/non-owner API/OTP; synthetic fixture scope only |
| Offline and permission denial | Behavioral/component cases pass, including durable-save failure/retry and rejected consent; user reports cache/relaunch, backend-loss access and denied-location manual planning pass; full disconnect, backup/restore and native expiry remain pending |
| Unit/component contracts and quality | Latest exact counts and command outcomes in [phase status](../PHASE_STATUS.md) and evidence |
| Web and Android build validation | JS exports passed historically; ARM64 custom debug APK build and physical install succeeded in continuation chat |
| Documented device startup works | Custom Android launch, Auth/planning/Maps and main lifecycle/accessibility walkthrough pass by user report; full disconnect/backup/expiry remain pending |
| Accessible/localized product acceptance | Typed dictionaries/tests pass; user confirms TalkBack, largest device font/layout and Kannada/Hindi wording; exact 200% font scale not measured |
| Release readiness | Not met: native/device evidence, dependency security resolution, hosted CI and external data gates remain open |

**Do not claim full Phase 04 acceptance.** Engineering implementation, automated integration, custom APK startup/Maps and the main user-reported walkthrough are verified; security, hosted CI and remaining lifecycle/expiry/backup/email gates are unresolved. No new database migration is needed. No commit, push or merge is performed.

## Remaining limitations and next verification
Follow the exact emulator/USB startup and manual checklist in [MOBILE.md](../MOBILE.md). The main device and language walkthrough passes by user report; fully disconnected cold launch, backup/restore and native expiry still need verification. Verify source data before real routing. Offline records require a restorable local identity; unavailable/expired Auth can require reconnecting. Review unresolved dependency advisories rather than forcing incompatible upgrades. Visual browser QA, signup email/deep-link delivery and hosted CI remain unverified. Future live/disruption fields remain inactive.

## Safety gate
Missing GPS means uncertainty, never cancellation. Simulation remains visible on every journey screen. Cache is stale historical information, never a silent current recommendation. Native map lines are approximate endpoint links, not validated paths. Real lift accessibility and congestion-safe rerouting are not claimed. Do not start Phase 05.


## Acceptance re-audit - 2026-10-30
See [current audit evidence](../evidence/phase04-audit-2026-10-30.json) and [phase status](../PHASE_STATUS.md). Mobile 31 passed/0 failed/0 skipped; backend 133 passed/2 failed/0 skipped. The two Auth-dependent failures and real-client bootstrap failure come from malformed ignored local test JSON. Client types/lint and both JS exports passed. Prettier fails 28 files (four still differ after LF normalization); byte-exact contract check fails while normalized content matches. Dependency audit reports 13 low/3 high affected-package entries. Historical genuine-service passes above are not current passing results.

Offline-save confirmation has a static control-flow defect: caught storage failures can be replaced by the saved-success message (`persist` -> `saveJourney`). This is not covered by the passing component tests. Native storage/permission/keyboard/TalkBack/maps, complete translation, signup delivery and hosted CI remain gates. No application or credential changes were made by this audit. No Phase 05, commit, push or merge.


## Blocker follow-up - 2026-10-30
The audit above is retained as a historical failing run. Current [follow-up evidence](../evidence/phase04-followup-2026-10-30.json): **38 mobile / 135 backend passed, zero failures/skips**, plus **11 real client/Auth/API/OTP checks**. Private Auth test input is repaired without changing server credentials/authorization. Durable-save false success is fixed and covered by save/retry plus consent-write regressions. Mobile formatting/LF, contract equality, semantic-drift rejection, types, lint, mypy, Expo compatibility and web/Android JS exports pass.

All app-owned dictionary strings now have Kannada/Hindi entries; completeness, Unicode, placeholders, fallback and localized screens are tested. Source fixture names/IDs and backend attribution/explanations remain untranslated source content. Native-speaker quality and native font/accessibility evidence remain required. Current ADB inventory has zero attached devices. The dependency audit still reports 13 low/3 high affected-package entries: no safe compatible Zod 3/Expo CLI or deepmerge patch is available. See [dependency review](../MOBILE.md#dependency-review-2026-10-30). **Full acceptance is not met**; no Phase 05, commit, push, merge or branch switch.


## Physical map investigation - 2026-10-31
[Current map evidence](../evidence/phase04-map-2026-10-31.json): key-free Expo Go map visibility fixed while preserving explicit opt-in, custom native build key requirement and endpoint-only fallback. 45 mobile tests passed with zero failures/skips; types/lint/format/contracts/SDK compatibility and Android JS export passed. User-reported core Android smoke passes are recorded separately from observed log diagnostics and mocked component tests. Google tile rendering after the fix still needs the [phone retest](../MOBILE.md#exact-usb-retest); no full acceptance is claimed.


Custom-build preparation (2026-10-31): documented Maps config plugin, expo-dev-client and a guarded development-only APK profile are prepared; no build, key/signing generation or cloud/billing configuration was started. The current credential absence is intentionally blocked by preflight. Follow [owner configuration and verification](../ANDROID_MAPS_DEVELOPMENT_BUILD.md); physical tiles remain unaccepted.


## Resume verification - 2026-11-03

See [fresh evidence](../evidence/phase04-resume-2026-11-03.json). Current automated checks: 48 mobile, 135 backend, and 11 actual client checks pass; zero test skips. ARM64 APK/install and map tiles are user-observed in the continuation chat. Remaining native/human, security and hosted-CI gates prevent full acceptance. Existing real-provider coverage gates remain unchanged.
