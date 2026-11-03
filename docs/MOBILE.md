# Phase 04 commuter client

The existing monorepo now contains `apps/mobile`, an Android-first Expo SDK 55 / React Native 0.83 / React 19 / strict TypeScript app. Expo's React Native Web target supplies a responsive commuter preview and read-only service-status shell. It is not an operations administration console. Phase 02 real-data rights/coverage blockers and Phase 03 synthetic-only routing limits remain unchanged.

## Start on Windows

Use Node 22+ (locally verified on Node 24.21.0 / npm 11.19.0), Python venv and Docker Desktop Linux containers. From the existing root:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
npm ci
Copy-Item apps/mobile/.env.example apps/mobile/.env
```

Edit the ignored mobile `.env` with **public** API/Auth origins and your Supabase publishable or legacy anon key. Everything named `EXPO_PUBLIC_*` is embedded in the app: never put a password, private JWT/signing key, database URL or service-role key there. The app rejects known service-role/secret key formats. Do not copy the backend `.env` into the client. For this repository's existing local direct Auth acceptance gateway only, `sb_publishable_local-development` is a non-secret placeholder: that gateway forwards Auth requests without an API-key layer, while FastAPI still verifies the genuine issued JWT. This placeholder is not a working key for a hosted Supabase project; use its real public key there.

Start existing PostgreSQL, local Auth and OTP as described in [DATABASE.md](DATABASE.md) and [ROUTING.md](ROUTING.md). Reuse the sealed Phase 03 release, not a new graph.

The older local Auth server rejects browser preflight headers such as `apikey` unless the gateway handles them. Install the credential-free [local preview gateway](../backend/dev/auth-gateway.conf) into the existing ignored Auth setup, validate and reload it (Auth must already be running):

```powershell
Copy-Item backups/phase01-auth/nginx.conf backups/phase01-auth/nginx.before-mobile-cors.conf
Copy-Item backend/dev/auth-gateway.conf backups/phase01-auth/nginx.conf
docker compose -f backups/phase01-auth/compose.yaml exec -T gateway nginx -t
if ($LASTEXITCODE -ne 0) { throw 'Gateway configuration validation failed' }
docker compose -f backups/phase01-auth/compose.yaml exec -T gateway nginx -s reload
```

This allowlists only `http://localhost:8081` and `http://127.0.0.1:8081`, supports the public SDK headers and leaves Auth/JWT verification intact. It is for this local gateway, not hosted Supabase configuration. The integration script checks both allowed origins and rejection of an untrusted origin; a successful server-to-server sign-in alone does not prove browser CORS works.

In the backend terminal:

```powershell
$local = Get-Content backups/phase01-auth/acceptance.json -Raw | ConvertFrom-Json
$env:DATABASE_URL = $local.database_url # Existing non-owner acceptance login
$env:SUPABASE_URL = $local.supabase_url # Must match the token issuer
$env:APP_ENV = 'development'
$env:SIMULATION_ENABLED = 'true'
$env:PYTHONPATH = 'backend'
$env:OTP_URL = 'http://127.0.0.1:18081'
$env:OTP_MANIFEST = (Resolve-Path backups/phase03-release/manifest.json).Path
$env:CORS_ALLOWED_ORIGINS = '["http://localhost:8081","http://127.0.0.1:8081"]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, select one target and set the corresponding public variables (environment variables override mobile `.env`):

```powershell
# Browser preview: http://localhost:8081
$env:EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8000'
$env:EXPO_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321'
$env:EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_local-development'
npm run web
```

```powershell
# Android Studio emulator: 10.0.2.2 reaches the Windows host loopback services.
$env:EXPO_PUBLIC_API_URL = 'http://10.0.2.2:8000'
$env:EXPO_PUBLIC_SUPABASE_URL = 'http://10.0.2.2:54321'
$env:EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_local-development'
npm run android --workspace @nammamove/mobile
```

An emulator with compatible Expo Go / development build, Android SDK and `adb` must already be installed. For an attached USB Android device, use `adb reverse tcp:8000 tcp:8000`, `adb reverse tcp:54321 tcp:54321` and `adb reverse tcp:8081 tcp:8081`, keep the loopback public URLs, and run `npm run mobile -- --localhost` (or `npx expo start --localhost` from `apps/mobile`). Open the localhost Metro URL in compatible Expo Go. Do not expose Docker/Auth/OTP ports to a public network. HTTP is allowed only for these explicit development loopback/emulator hosts; release configuration requires HTTPS. Changing public environment values requires restarting Metro; production exports bake them in. Native APK/AAB release builds are not produced by `expo export`.

## Manual acceptance walkthrough

1. Complete onboarding; select English, Kannada or Hindi. Sign in with an existing local test account without printing its credentials. New-account confirmation is handled with an email-confirmation notice; actual delivery/deep links require project configuration and remain unverified.
2. Keep authored stops A → D and **2026-10-26T07:55:00+05:30**. The fixed fixture date is visible intentionally. Pick departure/arrival, allowed bus/metro modes, walking allowance, source wheelchair requirement and preference. Search supports only four independently authored stops, not real Bengaluru geocoding.
3. Find journeys. Expected fastest accessible route: bus 08:00–08:05, walk to C, metro 08:12–08:17 IST, 17-minute physical duration plus 5-minute initial wait, 30 synthetic INR and one transfer. Cheapest returns the same fare; fewer transfers/less walking prefer the 50-INR express arriving 08:35. Ranking is bounded, not globally optimal.
4. Open details: each leg shows source route/trip/direction, times, coordinates and instructions. The geographic diagram shows approximate endpoints. Optional native Google Maps appears only when a restricted public Android map key is configured and the rider explicitly opens it. Connecting lines are not surveyed walking/track geometry. No map key is required for the diagram/list; web uses that accessible diagram instead of an external basemap. Real map rendering/billing restrictions remain a device/provider check. See [Expo maps](https://docs.expo.dev/versions/v55.0.0/sdk/map-view/).
5. Choose A → B with Bus enabled and Metro disabled: expect 08:00–08:05, 20 synthetic INR, no transfer. Choose 08:40 A → D: explicit no-route state. Arrival deadline 08:18 permits the transfer; 08:10 with wheelchair requirement does not. Date 27 Oct has no daytime service by fixture exception.
6. Deny location permission: manual origin remains usable. Granting permission performs one foreground location request and ranks only synthetic stops within 1 km by approximate straight-line distance; it never starts tracking or infers cancellations. Outside the tiny authored area, expect no nearby synthetic stops.
7. Favorite a destination; view Saved and recent searches. In Settings, explicitly enable encrypted offline retention, plan and choose Save offline. Open Saved while disconnected: cached results are prominently timestamped **CACHED / STALE**, not silently returned as a fresh recommendation. Cache is accessible only with a restorable local identity; an expired/nonrestorable Auth session can require reconnecting and signing in. Clearing storage/signing out removes this user's records. Native retention: at most 3 responses (2 alternatives each), 5 recent searches and 10 favorites; journeys expire after 24 hours. Do not use this fixture to travel.
8. Verify expired tokens refresh once; rejected refresh returns to sign-in. Stop only the test API/OTP to check meaningful unavailability, then restart it. Cold OTP JIT may also return 503; explicitly retry. Loading skeletons/disabled planning prevent duplicate submissions.
9. On Android, check 320-dp portrait, landscape, tablet and 200% font size; TalkBack focus/announcements, minimum 48-dp controls, keyboard avoidance, Android Back, permission denial, encrypted storage across relaunch, data removal, offline expiry and optional basemap rendering. These are required manual checks, not established by mocked component layout tests.

## Security, storage and scope

Supabase handles passwords/refresh; FastAPI receives bearer access tokens and remains the authorization authority. No service-role grants, user-selected roles or direct private-schema database access exist. Access tokens refresh once after 401, native automatic refresh follows foreground state, and redundant token-refresh events retain the selected journey. Invalid provider payloads fail closed, including any unsupported live labels. No request or token is logged by the client. API network bodies have a 12-second cancellation timeout and a post-read size bound; streaming transport byte enforcement is not claimed.

Native session/library values use Expo SecureStore with a serialized, chunked, index-last adapter to handle small encrypted-value limits; storage failures do not publish partial sessions. Native encryption/keystore/uninstall behavior must be checked on device. See [SecureStore](https://docs.expo.dev/versions/v55.0.0/sdk/securestore/). Saved records are per verified Auth subject, consented for journey retention and cleared on explicit sign-out. Favorites/recent searches are device-local (not cloud synced). Settings include clear-data controls. Abrupt process death can leave unreachable encrypted chunks; orphan garbage collection/full OS backup policy review is a pilot requirement. Browser preview uses memory only and intentionally loses sessions/saved records on reload; native encrypted offline storage is not imitated using browser localStorage.

English is complete for the current UI. Kannada/Hindi now provide complete typed app-owned UI dictionaries, including safety/details/maps/date-picker/error text, with tested English fallback for missing/blank entries. Native-speaker language review and native accessibility/font rendering remain required; fixture names/IDs and backend attribution/explanations remain source content. Geographical paths and fixture stop descriptions are not real transport data. Scheduled, approximate, unavailable, simulation and stale cache labels are distinct. No live map marker, disruption feed, GPS history, push notifications or automatic rerouting is implemented. Graph/trip/direction IDs remain available for later phases without activating them.

## Automated checks

```powershell
npm ci
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build # Web bundle; not a deployment
npm run build:android --workspace @nammamove/mobile # Hermes JS export, not APK/device proof
npm run contracts --workspace @nammamove/mobile -- --check
```

OpenAPI routing types are generated from the existing FastAPI factory with environment loading disabled. Regenerate intentionally with `npm run contracts --workspace @nammamove/mobile`. A runtime schema validates responses independently of static types. The npm lockfile and root React/React Native version overrides prevent incompatible peer hoisting. Use `npm ci`; do not force an SDK upgrade to suppress audit findings.

Real integration, with already running local services and correctly configured non-owner backend:

```powershell
$env:NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG = (Resolve-Path backups/phase01-auth/acceptance.json).Path
$env:NAMMAMOVE_MOBILE_TEST_API_URL = 'http://127.0.0.1:8000'
npm run integration --workspace @nammamove/mobile
```

This script makes genuine local Auth/API/OTP calls, requires explicit configuration and fails rather than substituting mocks/skips. It logs counts only. Unit/component transport mocks and native-module mocks establish behavior, not device integration. Keep the original Python quality and real PostGIS/Supabase/OTP tests enabled as described in [PHASE_STATUS.md](PHASE_STATUS.md).

The local npm audit currently identifies a high advisory in Expo CLI's transitive Zod 3 chain (three affected package entries); the application uses patched Zod 4. The installed CLI requires the older major, and npm's suggested automatic fix downgrades Expo across a major. Do not force that change or claim a clean dependency audit. Restrict development tooling to local use; review an upstream compatible patch/security resolution before release. Hosted CI and native APK/AAB build/install remain unverified. Latest measured results are in [Phase 04](phases/PHASE_04.md) and [phase status](PHASE_STATUS.md).

## Phase 04 audit launch commands (2026-10-30)

Current audit: backend/Auth/OTP each returned HTTP 200. Metro startup and the Android SDK 55 manifest returned 200 using the IPv4-first command below; that temporary server was then stopped. No Android device was connected and no emulator was available at the standard SDK path. These are repeatable manual instructions, not a completed native smoke test. Use [Expo Go for SDK 55](https://expo.dev/go?sdkVersion=55&platform=android&device=true), not an incompatible newer SDK client. Keep the backend, Auth and OTP running as configured above.

### USB phone

Enable USB debugging, connect the phone and approve its connection prompt. In a separate PowerShell terminal, use the existing local USB tools (or substitute your installed `adb.exe` path):

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
$adb = (Resolve-Path backups/android-tools/platform-tools/adb.exe).Path
& $adb devices
# Continue only when the intended phone shows "device", not "unauthorized".
& $adb reverse tcp:8000 tcp:8000
& $adb reverse tcp:54321 tcp:54321
& $adb reverse tcp:8081 tcp:8081

$env:EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8000'
$env:EXPO_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321'
$env:EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_local-development'
$env:NODE_OPTIONS = '--dns-result-order=ipv4first'
Set-Location apps/mobile
npx expo start --go --offline --port 8081
```

Leave the terminal and cable connected. Enter `exp://127.0.0.1:8081` in Expo Go 55. `--offline` disables Expo CLI online lookups, not app calls to local Auth/backend. Do not combine it with `--localhost`; Expo treats these as mutually exclusive host options. The placeholder public key is only for this repository's local acceptance gateway, never hosted Supabase.

### Already-running Android emulator

Install the Android SDK/emulator and compatible Expo Go first; these were not verified here. With only the intended emulator running, use a new PowerShell terminal:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
$adb = (Resolve-Path backups/android-tools/platform-tools/adb.exe).Path
& $adb devices
& $adb -e reverse tcp:8081 tcp:8081
$env:EXPO_PUBLIC_API_URL = 'http://10.0.2.2:8000'
$env:EXPO_PUBLIC_SUPABASE_URL = 'http://10.0.2.2:54321'
$env:EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_local-development'
$env:NODE_OPTIONS = '--dns-result-order=ipv4first'
Set-Location apps/mobile
npx expo start --go --offline --android --port 8081
```

### Minimum manual checks and initial audit blockers

Sign in, plan A–D at `2026-10-26T07:55:00+05:30`, inspect the 30-INR synthetic bus/walk/metro journey and 08:17 arrival, compare the 50-INR express, and test A–D at 08:40 for no-route. Deny location and retain manual origin. Opt into caching, save, relaunch and inspect the timestamped stale result; verify storage failures do not masquerade as saves, user changes/sign-out clear visibility, and native TalkBack/large fonts/keyboard/rotation behave correctly. Endpoint diagrams do not establish actual path or map-provider acceptance.

The current audit is not all green: 31 mobile tests passed; backend 133 passed/2 failed/0 skipped because ignored Auth acceptance JSON is malformed at line 12, column 7. Its parser failure also prevents the real-client integration script from starting its checks. Repair that local file privately before re-running; never paste credentials or raw parser excerpts into issues. App sign-in itself uses Supabase rather than reading this test file.

Prettier fails 28 files; 24 become compliant after LF normalization and four still have formatting differences. The contract check is byte-sensitive and fails although LF-normalized content matches. Establish consistent line endings and review formatting/contract regeneration before submission. Fresh `npm audit` reports 13 low and 3 high affected-package entries. A static UI finding also remains: caught storage errors in `persist` can be overwritten by `saveJourney`'s saved-success message. None of these findings was fixed by this audit. See [audit evidence](evidence/phase04-audit-2026-10-30.json); historical passing results are not current acceptance.


## Blocker follow-up results (2026-10-30)
The preceding audit blockers describe the initial run, retained for traceability. [Current evidence](evidence/phase04-followup-2026-10-30.json): 38 mobile and 135 backend tests passed with zero failures/skips, plus 11 genuine TypeScript client/Auth/API/OTP checks. Private Auth configuration was repaired locally, durable-save confirmation fixed, LF/formatting normalized and schema verification made CRLF-tolerant while preserving actual drift rejection. All types/lint/format/mypy/contract/Expo compatibility and web/Android JS export checks pass. Complete app-owned Kannada/Hindi strings and fallback/localized-screen tests pass; source fixture/provider text is preserved. No device was attached for this follow-up, and JS exports do not verify native install or lifecycle.

### Dependency review (2026-10-30)
Fresh `npm audit --json` reports 13 low and 3 high affected-package entries (not 16 independent vulnerabilities), zero critical. The two root advisories are:

- [Zod oversized-collection memory exhaustion](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5): versions below 4.6.6 are affected. Application response validation uses 4.6.7. Expo CLI 55.0.37 requires the incompatible older Zod 3.25.76 chain; forcing Zod 4 or npm's suggested Expo SDK downgrade is not a safe compatible fix. Await/review an upstream compatible resolution.
- [Deepmerge prototype poisoning](https://github.com/advisories/GHSA-gcqx-w48m-w2h4): installed 4.3.1 is affected and the advisory lists no patched release (registry latest is 4.3.1). It is used through Expo configuration and Jest. Do not merge untrusted configuration/objects; restrict development tooling and feeds to trusted local inputs. This mitigation does not establish security acceptance.

No safe compatible advisory fix was found, and no dependency overrides, audit suppression, forced SDK changes or unnecessary lockfile update was applied. Recheck upstream advisories before release. Dependency acceptance remains open.

### Android acceptance prerequisites
Use Node 22+/npm 10+, the existing Python virtual environment and Docker Desktop with PostgreSQL/PostGIS, the local Supabase gateway on 54321 and sealed synthetic OTP on 18081. Start the non-owner API on 8000 using the startup commands above. A valid local test account and Expo Go compatible with SDK 55 are required. For USB: an Android phone, data-capable cable, USB debugging enabled, RSA prompt approved and `adb devices` showing exactly the intended authorized device. Reverse ports 8000, 54321 and 8081, then launch Metro with the public loopback settings above; leave all services and the cable connected. For emulator: install Android Studio/SDK/system image and start an AVD; use 10.0.2.2 for API/Auth and reverse Metro 8081 as shown above. Optional Google basemap acceptance needs a suitable native build and appropriately restricted key. Expo Go smoke does not prove standalone APK keystore/backup behavior.

Verify the minimum checklist above plus Kannada/Hindi planning/detail/error text, failed-save behavior, TalkBack, large fonts, keyboard/rotation and native cache/relaunch/sign-out. Record observed results; do not infer them from component mocks. Full Phase 04 acceptance, signup delivery/deep links and hosted CI remain pending. No real Bengaluru/live coverage or Phase 05 feature is enabled.


## Physical Android map investigation (2026-10-31)
The user reports physical-device passes for Auth, synthetic A-D planning, alternatives, details and simulation labels; the map failed. ADB confirms a connected phone running Expo Go 55.0.7 with Google Play Services. Fine/coarse location permission is denied, which does not prevent fixed-route maps because `showsUserLocation` is false and map setup never asks for GPS. Captured process logs contain native manager setter warnings but no map authorization/missing-component error or fatal crash; this does not establish successful tile loading.

**Confirmed code defect:** optional basemap controls were hidden whenever the project had no Google Maps key, including in Expo Go. [SDK 55 documentation](https://docs.expo.dev/versions/v55.0.0/sdk/map-view/) confirms react-native-maps 1.27.2 is included in Expo Go with no additional setup. Runtime detection now permits the opt-in map in Expo Go without a project key. Custom native binaries still require the configured key and a native rebuild. The existing Android config key path is supported by the installed Expo prebuild plugin; no permission/provider/native config changes were necessary. The native map now has explicit full width and fixed height, and unconfigured custom builds show a translated explanation beside the endpoint diagram.

A numbered diagram with coordinates and approximate endpoint links is an intentional fallback, not a Google street map. After the fix, Expo Go also offers **Show optional basemap**. A Google logo or empty gray area after pressing that button is a separate actual tile-loading failure, not acceptable proof that the map works. Initial fixture coordinates 12.970/77.590 through 12.971/77.620 are valid and within the starting viewport. Lines are approximate and never assert real road/track paths.

### Exact USB retest
Keep Docker/Auth/OTP and the backend running. Stop only the Expo terminal with Ctrl+C. In PowerShell:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
$adb = (Resolve-Path backups/android-tools/platform-tools/adb.exe).Path
& $adb devices
& $adb -d reverse tcp:8000 tcp:8000
& $adb -d reverse tcp:54321 tcp:54321
& $adb -d reverse tcp:8081 tcp:8081
$env:EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8000'
$env:EXPO_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321'
$env:EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_local-development'
$env:NODE_OPTIONS = '--dns-result-order=ipv4first'
Set-Location apps/mobile
npx expo start --go --offline --clear --port 8081
```

Use the placeholder public key only with the existing local Auth gateway. Expo Go does not require setting EXPO_PUBLIC_GOOGLE_MAPS_KEY. Open `exp://127.0.0.1:8081` in Expo Go 55, sign in, plan A-D at `2026-10-26T07:55:00+05:30`, open Journey details and press **Show optional basemap**. The phone needs internet for Google tiles even though Metro uses `--offline`. Expect Google street tiles with synthetic markers/approximate straight endpoint links. Verify Hide/Show and the simulation/path warnings; denial of location permission should not block the map. Only numbered circles without streets verify the fallback, not Google tiles.

If tiles remain blank, keep that screen open and collect map logs privately, not into tracked files:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
$adb = (Resolve-Path backups/android-tools/platform-tools/adb.exe).Path
$expoPid = (& $adb -d shell pidof host.exp.exponent).Trim()
if (-not $expoPid) { throw 'Expo Go is not running.' }
& $adb -d logcat -d --pid=$expoPid > backups/phase04-map-retest-private.log
```

Raw logs may include keys/session details; keep them ignored and share only redacted error summaries. For a custom Android binary, enable Maps SDK for Android in the authorized Google project, meet its billing requirements, restrict the key to `work.nammamove.commuter` plus the actual signing SHA-1, set the ignored Maps key before rebuilding, and reinstall. Reloading Metro cannot update a native manifest. No such build/account configuration was performed in this investigation.

[Map evidence](evidence/phase04-map-2026-10-31.json): 45 mobile tests passed, zero failed/skipped; types/lint/format/contracts/SDK compatibility and Android JS export passed. Component/native-module mocks are not physical tile evidence. Post-fix physical basemap rendering remains pending; no full Phase 04 acceptance or Phase 05 work.


### Confirmed blank-map cause - 2026-10-31
After opening the fixed basemap control, the user screenshot shows a blank Google-logo map. Fresh connected-device logs explicitly report **Google Android Maps SDK: Authorization failure**, identifying the host application as `host.exp.exponent` (Expo Go). The renderer initializes, but its native Maps authorization is rejected. No Maps key or raw log is included in public evidence. This verifies the visibility fix and establishes a separate actual provider-authorization blocker; coordinate/GPS permission changes are not a supported remedy.

The project cannot replace Expo Go's embedded Maps key through a JavaScript environment variable. Use an upstream repaired compatible Expo Go client, or a custom development build with an authorized Maps SDK for Android key restricted to the actual package/signing SHA-1, native rebuild and reinstall. Google project/key provisioning is owner-controlled; none was created or changed here. Keep the endpoint diagram as the available fallback, and do not mark physical map acceptance passed. No app code or tests changed in this diagnostic-only follow-up; the preceding 45 passing mobile tests do not prove tile authorization. See [map evidence](evidence/phase04-map-2026-10-31.json).


### Custom Android map build preparation - 2026-10-31
The supported Maps config plugin, SDK-compatible expo-dev-client, development/internal APK profile and key-redacting `npm run maps:check` are prepared. Signing credentials/native outputs are ignored. No owner-authorized Maps key or NammaMove signing SHA-1 is available in the checked local configuration; remote account configuration remains unverified. **No build was started.** Follow the exact [manual Google Cloud/EAS/file configuration and verification guide](ANDROID_MAPS_DEVELOPMENT_BUILD.md). Expo Go launch defaults remain explicit `--go`, and the Hide basemap/endpoint fallback is preserved. Use the separate development-client launch command only after a configured custom APK is installed.


## Phase 04 pre-build blocker measures - 2026-11-01
The user authorized the next environment/upload measures after the read-only audit. Preserved the existing private Maps key and appended the documented USB-only API/Auth/public-gateway settings to the ignored mobile environment. Created the four previously missing EAS development variables; the Maps key is Sensitive and the three public values are Plain text. Existing cloud values were not overwritten. Fresh remote verification and cloud-only EAS config (inherited public values removed) pass; the Maps plugin receives the same key without printing it. No new Google key, billing action or signing credential was created.

Created root [.easignore](../.easignore) with all existing Git private/cache/signing protections plus unrelated backend/docs/legacy frontend exclusions. EAS's Windows copy filter receives directory names without a trailing slash; directory-only ignore patterns did not prevent an unreadable cache from being opened. Added equivalent plain directory-name patterns, then successfully ran the actual EAS filtered-copy function into a temporary directory: 46 app/workspace files, required source/manifests/lockfile retained, no private key/environment/signing/backups/caches/Git or unrelated sources. No cache was deleted or granted new permissions, no Git clone/history mutation occurred and no archive was uploaded.

Local maps:check passes. Mobile **48 passed / 0 failed / 0 skipped**; TypeScript, lint and formatting pass. API/Auth loopback values are for USB-only development and require the phone's reverse ports 8000, 54321 and Metro 8081 plus running backend/Auth/OTP. They are not hosted services and were not claimed reachable in this configuration-only step. Google Maps SDK enablement/approved billing and package/signing SHA-1 restrictions still require owner confirmation; actual installed APK tile behavior remains unverified. Existing security/native/human acceptance gates remain open.

No build, commit, push, merge or Phase 05 work. [Sanitized preparation evidence](evidence/phase04-prebuild-preparation-2026-11-01.json) records the changes.
