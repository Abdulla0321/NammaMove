# Phase 04: custom Android map development build

Current status (2026-11-03): the user reports a successful custom ARM64 debug APK build/install and visible Maps tiles/markers. Full Phase 04 acceptance remains pending security, hosted CI and remaining lifecycle gates; see [resume evidence](evidence/phase04-resume-2026-11-03.json). The preparation observations below are historical. Existing synthetic routing and the Hide basemap/endpoint diagram are preserved. Expo Go's rejected embedded key is not modified.

## Verified locally
- Expo SDK 55; react-native-maps 1.27.2 matches Expo's recommendation; Android package remains `work.nammamove.commuter`.
- [App configuration](../apps/mobile/app.config.ts) now uses the documented `react-native-maps` plugin with `androidGoogleMapsApiKey`, sourced from `EXPO_PUBLIC_GOOGLE_MAPS_KEY`. The previous legacy key location is removed to avoid duplicate configuration. No key literal is in source.
- SDK-compatible expo-dev-client is installed. [eas.json](../apps/mobile/eas.json) has internal preview and development APK profiles; development explicitly selects the development environment/client and sets a missing-key guard. No production workflow is added. Dependency install used npm with lifecycle scripts disabled after Expo's installer encountered npm EALLOWSCRIPTS; no native compilation occurred during that preparation.
- No nonempty Maps key was found in the checked repository/mobile dotenv files or this process. No project credentials file, generated Android project, local debug keystore or standard Android SDK directory was found; JAVA_HOME is unset. This does not establish that no authorized key/keystore exists in your Google Cloud/EAS account: remote accounts were not accessed.
- Signing files, credentials.json and generated native directories are ignored. Existing Expo Go launch scripts explicitly retain `--go`; `start:dev-client` is separate. No maps/GPS permission relaxation is added.

## Manual owner configuration, in order

### 1. Google Cloud Console: project and authorized key
Open [Google Cloud Console](https://console.cloud.google.com/), select the owner-approved project, then:
1. **APIs & Services > Library:** verify **Maps SDK for Android** is enabled.
2. **Billing:** verify the project meets Google's billing prerequisites. If not already approved/configured, stop for an owner decision; no billing action has been taken here.
3. **APIs & Services > Credentials:** identify an existing owner-authorized Android Maps API key. Reuse it only if the owner permits adding this development app. If no suitable key exists, the owner must provision one manually; do not copy Expo Go's key or another app's credentials.
4. Keep the value private. It will be needed in the local mobile environment and, for EAS cloud builds, the EAS development environment. This mobile API key is embedded in the binary/bundle and is extractable; Android/API restrictions, not secrecy in the APK, protect its use.

### 2. Expo/EAS: project link and signing certificate
EAS cloud building avoids needing the missing local Android SDK/JDK. Use your authorized [Expo account/project](https://expo.dev/). From **Windows PowerShell in the existing mobile workspace**:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove\apps\mobile'
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest credentials --platform android
```

These are manual account/link/credential-management steps, not build commands. Select the owner-approved existing NammaMove EAS project; if none exists, have the owner decide how to provision its cloud record. Do not create another local project/repository. Linking records the real EAS project ID in app configuration. For the development profile, select the authorized existing Android keystore, or have the owner explicitly provision the signing credential through EAS credential management. This Android signing key is separate from the Google Maps API key. Do not overwrite an existing keystore or post passwords/private keys.

Obtain the certificate's **SHA-1** from the Expo project **Credentials > Android > application identifier/keystore** or the credential-management CLI. It must be the certificate that will sign the development APK, not Expo Go's certificate and not a different Play/App Signing certificate. EAS metadata/credential evaluation is allowed before the Maps key is available. The local maps:check preflight and actual Android build-job key guard still require the owner-authorized key. No EAS credentials were accessed/verified in this session.

### 3. Google Cloud Console: bind key to this exact app
Return to **APIs & Services > Credentials > selected API key**:
- **Application restrictions:** Android apps.
- Add package **work.nammamove.commuter** and the development APK signing **SHA-1 from step 2**.
- **API restrictions:** restrict to **Maps SDK for Android**.
- Save and allow configuration propagation. Verify the project, SDK enablement, billing status and both restrictions. Do not temporarily leave the key unrestricted as a workaround.

[Google's setup instructions](https://developers.google.com/maps/documentation/android-sdk/get-api-key) explain the required project/key and Android package/SHA-1 restrictions.

### 4. Files and EAS environment: provide configuration without committing it
Locally, privately edit **apps/mobile/.env** using [the example](../apps/mobile/.env.example). Put the authorized value on `EXPO_PUBLIC_GOOGLE_MAPS_KEY=`. Keep the existing public API/Auth values, including the local gateway's non-secret public placeholder key, for USB development. Never copy backend database credentials into the mobile file.

For a future cloud build, open the linked Expo project **Environment variables**, choose **development**, and supply the same `EXPO_PUBLIC_GOOGLE_MAPS_KEY` with **Sensitive** visibility (available to authenticated config resolution). Also set the public API/Auth values used for this development target: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. The existing USB targets are loopback ports 8000 and 54321; only use that local placeholder Auth key with this repository's local gateway. Never upload the backend .env. Ignored local dotenv files are not uploaded automatically to EAS.

Keep the Maps value out of app.config.ts, eas.json, commits and console screenshots. Do not run a raw `expo config --json` command to share diagnostics because resolved configuration can contain the key. [EAS environment documentation](https://docs.expo.dev/eas/environment-variables/) explains local versus cloud availability.

### 5. Verify configuration before any build
From **PowerShell in apps/mobile**:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove\apps\mobile'
npm run maps:check
```

Currently this exits **1**, reporting the missing key; that is the expected blocked result. After private configuration, expect `Local Maps plugin/key presence and Android package check passed.` It prints no key and starts no build. This checks local configuration presence only; it does **not** prove Google authorization, signing correctness, billing approval or the EAS environment values. Independently verify those settings in the websites above. A missing key also fails configuration on an actual Android build worker for the guarded EAS development profile; read-only EAS config/credential metadata inspection remains allowed. Do not start a build until all manual requirements are satisfied; no build command was executed or queued here.

## Device verification after an approved build/install
Once the configured development APK has been separately built and installed, select **NammaMove**, not Expo Go. Ensure the phone is authorized in `adb devices`, keep backend/Auth/OTP running, and reverse ports 8000, 54321 and 8081. Run from **apps/mobile**:

```powershell
npm run start:dev-client -- --offline --port 8081
```

Open the local Metro server in the installed development client's launcher. For continued Expo Go/fallback testing before then, use `npm run start -- --offline --port 8081` (explicit `--go` is retained). Do not expect Expo Go's Google authorization failure to change from these project settings.

In the custom app, plan A-D at 2026-10-26 07:55 IST, open Journey details, then Show optional basemap. With internet access, verify visible Google street tiles, synthetic markers/approximate links and Hide basemap returning to the working endpoint diagram. Do not require GPS permission for this fixed-route view. Capture SDK diagnostics privately if it fails; the application identity should be `work.nammamove.commuter`, with no Maps authorization failure. Absence of log errors alone is not a visual pass. A changed key or signing identity requires native rebuild/reinstall and matching key restrictions; Metro reload cannot rewrite native credentials.

## Preparation evidence
45 mobile tests pass with zero failures/skips. TypeScript, ESLint, Prettier, routing-contract and SDK compatibility checks pass. The key-presence check and missing-key build guard both reject the current absent credential. No APK/AAB/native or JavaScript build was started during this preparation. Previous JS exports and backend passes remain separate historical evidence. Dependency audit remains 13 low/3 high affected-package entries; no unsafe audit override was applied. Full physical basemap and Phase 04 acceptance remain blocked pending the manual configuration and installed custom-app test.

References: [Expo SDK 55 Maps](https://docs.expo.dev/versions/v55.0.0/sdk/map-view/), [development builds](https://docs.expo.dev/develop/development-builds/introduction/), [EAS profiles](https://docs.expo.dev/build/eas-json/).


## EAS config bootstrap fix - 2026-11-01
EAS CLI 27.2.0 on Node 24.21.0 launches the resolved Expo CLI from apps/mobile with `config --json --type public`, inherits the parent/profile environment and adds `EXPO_NO_DOTENV=1`. The development profile supplies `NAMMAMOVE_REQUIRE_ANDROID_MAPS=true`. Previously the top-level app-config guard threw before EAS could read the project ID and fetch cloud variables. Expo JSON mode temporarily suppresses logging, so the subprocess returned exit 1 with no stdout/stderr and EAS showed only a generic subprocess failure. This was a project-config bootstrap error, not a Windows Node-spawn failure.

The guard now requires actual build-worker context (`EAS_BUILD=true`, `EAS_BUILD_PLATFORM=android`) as well as the profile flag. Google key validation is retained on Android workers and maps:check remains credential-gated. Project linkage, Maps plugin, package and runtime functionality are unchanged. The exact EAS helper and full read-only config command pass after the fix; no global/npm/EAS executable patch, credentials operation or build was performed.

From PowerShell in apps/mobile, verify without printing resolved configuration or keys:

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove\apps\mobile'
eas config --platform android --profile development --non-interactive --json > $null
if ($LASTEXITCODE -eq 0) { 'EAS config: PASS' } else { 'EAS config: FAILED' }
```

48 mobile tests pass with zero failures/skips, including metadata bootstrap, missing-key Android worker rejection and iOS isolation. TypeScript/lint/format checks pass. [Reproduction evidence](evidence/phase04-eas-config-2026-11-01.json) contains sanitized invocation/environment details; raw resolved configs remain private. See [Expo's build-only environment documentation](https://docs.expo.dev/eas/environment-variables/usage/) for the worker variables.


## Environment/upload measures completed - 2026-11-01
The previously missing EAS development variables are now configured: the existing Maps key was reused as Sensitive; API/Auth URL and public local-gateway values were added as Plain text. The ignored mobile environment now persists the same USB loopback setup. Fresh cloud-only EAS config and local maps:check pass; no values were printed. Root [.easignore](../.easignore) retains private-file protections and excludes unrelated sources and cache directories before Windows copy traversal. Actual EAS filtered local-copy validation passes with 46 files and no secrets/cache permission error. No signing/billing changes or build/upload occurred. See [preparation evidence](evidence/phase04-prebuild-preparation-2026-11-01.json).

Before any APK build, the owner must still confirm Maps SDK enablement, approved Google project billing and the key's Android restriction pair: package `work.nammamove.commuter`, selected EAS signing SHA-1 `1E:35:CB:1F:E7:25:E3:A3:03:46:C9:DC:80:C7:F9:B1:37:5B:77:19`. These restrictions were not changed or bypassed. For the eventual phone test, connect/authorize the device, start Docker/backend/Auth/OTP and reverse USB ports as documented; no physical connectivity or tile acceptance is implied by a cloud configuration pass.
