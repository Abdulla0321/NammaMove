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

English is complete for the current UI. Kannada/Hindi provide a typed translation structure and core navigation/planning labels with deterministic English fallback; remaining safety/detail text needs professional translation and accessibility review before localized acceptance. Geographical paths and fixture stop descriptions are not real transport data. Scheduled, approximate, unavailable, simulation and stale cache labels are distinct. No live map marker, disruption feed, GPS history, push notifications or automatic rerouting is implemented. Graph/trip/direction IDs remain available for later phases without activating them.

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
