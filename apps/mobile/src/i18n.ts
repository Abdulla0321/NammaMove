export type Language = 'en' | 'kn' | 'hi';
export const en = {
  home: 'Plan',
  saved: 'Saved',
  settings: 'Settings',
  welcome: 'A calmer way to get there.',
  intro:
    'Compare bus, metro and walking journeys. This development app uses an invented test network, never live Bengaluru service.',
  continue: 'Get started',
  signIn: 'Sign in',
  signUp: 'Create account',
  email: 'Email',
  password: 'Password',
  origin: 'Starting point',
  destination: 'Where are you going?',
  plan: 'Find journeys',
  depart: 'Depart after',
  arrive: 'Arrive by',
  when: 'Date and time with timezone',
  fastest: 'Fastest',
  cheapest: 'Cheapest',
  fewest_transfers: 'Fewer transfers',
  least_walking: 'Less walking',
  accessible: 'Require source wheelchair accessibility',
  location: 'Find nearby stops',
  simulation: 'SIMULATION · Invented network',
  notice: 'Scheduled test times · No live tracking · Service status unknown',
  noRoute:
    'No feasible journey for these choices. Try another time, mode or walking limit.',
  offline:
    'Offline or backend unavailable. Retry, or open a previously saved journey.',
  unauthorized: 'Your session expired. Sign in again.',
  invalid: 'Check the places, time with timezone and walking limit.',
  incompatible:
    'The backend returned an unsupported response. Update or contact support.',
  denied:
    'Location unavailable or permission denied. Choose your starting point manually.',
  noNearby:
    'No synthetic stops within 1 km. This is not a real nearby-transit directory.',
  loading: 'Finding feasible journeys…',
  alternatives: 'Your journey options',
  detail: 'Journey details',
  back: 'Back',
  unknownFare: 'Fare unavailable',
  walking: 'Walking',
  transfers: 'Transfers',
  save: 'Save offline',
  favorite: 'Favorite destination',
  clear: 'Clear saved data',
  signOut: 'Sign out & clear device data',
  cache: 'Allow encrypted on-device journey cache (24 hours)',
  cacheNotice:
    'Saved trips contain places and travel times. Opt in to retain up to 3 journeys; no live updates while offline.',
  empty:
    'Nothing saved yet. Your places and recent searches stay on this device.',
  stale: 'CACHED / STALE · Not a current recommendation',
  language: 'Language',
  choose: 'Choose this place',
  network: 'Routing preferences',
  maxWalk: 'Maximum walking (metres)',
  bus: 'Bus',
  metro: 'Metro',
  walk: 'Walk',
  timing:
    'Approximate map links, not surveyed paths. Times are scheduled fixture values.',
  webStatus: 'Service status',
  retry: 'Retry',
  remember: 'Saved on this device',
  storageSaveFailed:
    'Could not save encrypted device data. Free storage and retry.',
  storageReadFailed: 'Could not read encrypted device storage.',
  authValidation:
    'Enter a valid email and password (8+ characters for a new account).',
  confirmEmail: 'Check your email to confirm your account, then sign in.',
  signInFailed: 'Sign-in failed. Check your credentials and connection.',
  signUpFailed: 'Account creation unavailable. Check the form and connection.',
  cacheExpired: 'This cached journey has expired. Reconnect and plan again.',
  restoring: 'Restoring session',
  preview: 'BENGALURU / COMMUTER PREVIEW',
  clearChoices: 'One journey. Clear choices.',
  modesSummary: 'Bus + Metro + Walk',
  gpsNotice:
    'No background location collection. Missing GPS never confirms cancellation.',
  onboardSaveFailed: 'Onboarding preference could not be saved.',
  authNotice:
    'Use your Supabase account. Your password is sent only to your configured Auth provider.',
  webMemory:
    'Web preview uses memory only: sessions and saved data are cleared on reload. Persistent encrypted offline storage is native-only.',
  backendReady: 'Backend ready · OTP availability requires a journey request',
  backendUnavailable: 'Backend unavailable',
  signOutFailed: 'Could not clear this session. Retry.',
  remove: 'Remove {place}',
  savedAt: 'Saved {date}',
  openCached: 'Open cached journey {number}',
  walkInstruction:
    'Walk approximately {distance} m between the listed endpoints.',
  boardInstruction:
    'Board {route}; trip {trip}, direction {direction}. Alight at the listed endpoint.',
  unavailable: 'unavailable',
  unknown: 'unknown',
  accessibilityNotice:
    'Source accessibility is static; live lifts and vehicle positions are unavailable. Do not use this invented network for travel.',
  ranking:
    'Ranking: {preference}. Bounded candidates; no global optimum guarantee. All times IST.',
  firstPreference: 'FIRST FOR YOUR PREFERENCE',
  alternative: 'ALTERNATIVE',
  syntheticFare: 'synthetic fare',
  initialWait: 'Initial wait',
  minutes: 'min',
  metres: 'm',
  noMatchingStop:
    'No matching synthetic stop. Only authored stops A–D are available.',
  nextJourney: 'YOUR NEXT JOURNEY',
  fixtureExample:
    'Fixture example: 26 Oct 2026, 07:55 IST. Date 27 Oct has no daytime service by design. Native picker uses your device timezone; results show IST.',
  nearbyDistance: '{place} · approximately {distance} m straight-line',
  nearbyNotice:
    'Only the four authored stops A–D are searchable. Nearby results are synthetic endpoints, not real transport availability. Location is used once, in memory, after permission.',
  chooseDate: 'Choose date',
  chooseTime: 'Choose time',
  mapOverview: 'Synthetic geographic overview · North ↑',
  mapApproximate: 'Approximate endpoints only; not a street or track path.',
  mapEndpoints:
    'Synthetic route endpoints, north up. Coordinates listed below.',
  mapPrivacy:
    'Optional Google basemap sends the viewed area to the map provider. Lines below connect endpoints approximately; no route geometry was supplied.',
  hideMap: 'Hide basemap',
  showMap: 'Show optional basemap',
  mapLabel: 'Synthetic journey on geographic basemap',
  mapStep: 'Synthetic step {number}: {mode}',
  mapDestination: 'Synthetic destination',
  mapUnavailable:
    'Basemap unavailable in this build. Use Expo Go, or configure an Android Maps SDK key and rebuild the app. The numbered diagram shows approximate endpoints only.',
};
export type Key = keyof typeof en;
export const kn: Record<Key, string> = {
  home: 'ಯೋಜನೆ',
  saved: 'ಉಳಿಸಿದವು',
  settings: 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು',
  welcome: 'ನಿಮ್ಮ ಪ್ರಯಾಣವನ್ನು ಸುಲಭಗೊಳಿಸಿ.',
  continue: 'ಪ್ರಾರಂಭಿಸಿ',
  signIn: 'ಪ್ರವೇಶಿಸಿ',
  signUp: 'ಖಾತೆ ತೆರೆಯಿರಿ',
  email: 'ಇಮೇಲ್',
  password: 'ಪಾಸ್‌ವರ್ಡ್',
  origin: 'ಆರಂಭದ ಸ್ಥಳ',
  destination: 'ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?',
  plan: 'ಪ್ರಯಾಣಗಳನ್ನು ಹುಡುಕಿ',
  depart: 'ಹೊರಡುವ ಸಮಯ',
  arrive: 'ತಲುಪುವ ಸಮಯ',
  fastest: 'ಅತಿ ವೇಗ',
  cheapest: 'ಕಡಿಮೆ ದರ',
  fewest_transfers: 'ಕಡಿಮೆ ಬದಲಾವಣೆ',
  least_walking: 'ಕಡಿಮೆ ನಡಿಗೆ',
  back: 'ಹಿಂದೆ',
  simulation: 'ಅನುಕರಣೆ · ಕಲ್ಪಿತ ಜಾಲ',
  loading: 'ಪ್ರಯಾಣಗಳನ್ನು ಹುಡುಕಲಾಗುತ್ತಿದೆ…',
  language: 'ಭಾಷೆ',
  intro:
    'ಬಸ್, ಮೆಟ್ರೋ ಮತ್ತು ನಡಿಗೆಯ ಪ್ರಯಾಣಗಳನ್ನು ಹೋಲಿಸಿ. ಈ ಆ್ಯಪ್ ಕಲ್ಪಿತ ಪರೀಕ್ಷಾ ಜಾಲವನ್ನು ಬಳಸುತ್ತದೆ; ಬೆಂಗಳೂರಿನ ನೇರ ಸೇವೆಯಲ್ಲ.',
  when: 'ಸಮಯ ವಲಯದೊಂದಿಗೆ ದಿನಾಂಕ ಮತ್ತು ಸಮಯ',
  accessible: 'ಮೂಲ ದತ್ತಾಂಶದ ಪ್ರಕಾರ ಗಾಲಿಕುರ್ಚಿ ಪ್ರವೇಶ ಅಗತ್ಯ',
  location: 'ಹತ್ತಿರದ ನಿಲ್ದಾಣಗಳನ್ನು ಹುಡುಕಿ',
  notice:
    'ನಿಗದಿತ ಪರೀಕ್ಷಾ ಸಮಯಗಳು · ನೇರ ಟ್ರ್ಯಾಕಿಂಗ್ ಇಲ್ಲ · ಸೇವೆಯ ಸ್ಥಿತಿ ತಿಳಿದಿಲ್ಲ',
  noRoute:
    'ಈ ಆಯ್ಕೆಗಳಿಗೆ ಸಾಧ್ಯವಾದ ಪ್ರಯಾಣವಿಲ್ಲ. ಬೇರೆ ಸಮಯ, ಸಾರಿಗೆ ವಿಧಾನ ಅಥವಾ ನಡಿಗೆ ಮಿತಿಯನ್ನು ಪ್ರಯತ್ನಿಸಿ.',
  offline:
    'ಇಂಟರ್ನೆಟ್ ಅಥವಾ ಬ್ಯಾಕೆಂಡ್ ಲಭ್ಯವಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಉಳಿಸಿದ ಪ್ರಯಾಣ ತೆರೆಯಿರಿ.',
  unauthorized: 'ನಿಮ್ಮ ಪ್ರವೇಶ ಅವಧಿ ಮುಗಿದಿದೆ. ಮತ್ತೆ ಪ್ರವೇಶಿಸಿ.',
  invalid: 'ಸ್ಥಳಗಳು, ಸಮಯ ವಲಯವಿರುವ ಸಮಯ ಮತ್ತು ನಡಿಗೆ ಮಿತಿ ಪರಿಶೀಲಿಸಿ.',
  incompatible:
    'ಬ್ಯಾಕೆಂಡ್ ಬೆಂಬಲಿಸದ ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಿದೆ. ನವೀಕರಿಸಿ ಅಥವಾ ಸಹಾಯ ಪಡೆಯಿರಿ.',
  denied:
    'ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ಆರಂಭದ ಸ್ಥಳವನ್ನು ನೀವೇ ಆಯ್ಕೆಮಾಡಿ.',
  noNearby: 'ಒಂದು ಕಿ.ಮೀ. ಒಳಗೆ ಕಲ್ಪಿತ ನಿಲ್ದಾಣಗಳಿಲ್ಲ. ಇದು ನೈಜ ಸಾರಿಗೆ ಪಟ್ಟಿಯಲ್ಲ.',
  alternatives: 'ನಿಮ್ಮ ಪ್ರಯಾಣದ ಆಯ್ಕೆಗಳು',
  detail: 'ಪ್ರಯಾಣದ ವಿವರಗಳು',
  unknownFare: 'ಪ್ರಯಾಣ ದರ ಲಭ್ಯವಿಲ್ಲ',
  walking: 'ನಡಿಗೆ',
  transfers: 'ಬದಲಾವಣೆಗಳು',
  save: 'ಆಫ್‌ಲೈನ್‌ಗಾಗಿ ಉಳಿಸಿ',
  favorite: 'ಮೆಚ್ಚಿನ ಗಮ್ಯಸ್ಥಾನ',
  clear: 'ಉಳಿಸಿದ ದತ್ತಾಂಶ ಅಳಿಸಿ',
  signOut: 'ನಿರ್ಗಮಿಸಿ ಮತ್ತು ಸಾಧನದ ದತ್ತಾಂಶ ಅಳಿಸಿ',
  cache: 'ಸಾಧನದಲ್ಲಿ ಎನ್‌ಕ್ರಿಪ್ಟ್ ಮಾಡಿದ ಪ್ರಯಾಣ ಸಂಗ್ರಹಕ್ಕೆ ಅನುಮತಿಸಿ (24 ಗಂಟೆ)',
  cacheNotice:
    'ಉಳಿಸಿದ ಪ್ರಯಾಣಗಳಲ್ಲಿ ಸ್ಥಳಗಳು ಮತ್ತು ಸಮಯಗಳಿರುತ್ತವೆ. ಗರಿಷ್ಠ 3 ಪ್ರಯಾಣ ಉಳಿಸಲು ಅನುಮತಿಸಿ; ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ನೇರ ನವೀಕರಣಗಳಿಲ್ಲ.',
  empty:
    'ಇನ್ನೂ ಏನೂ ಉಳಿಸಿಲ್ಲ. ನಿಮ್ಮ ಸ್ಥಳಗಳು ಮತ್ತು ಇತ್ತೀಚಿನ ಹುಡುಕಾಟಗಳು ಈ ಸಾಧನದಲ್ಲೇ ಇರುತ್ತವೆ.',
  stale: 'ಸಂಗ್ರಹಿತ / ಹಳೆಯದು · ಪ್ರಸ್ತುತ ಶಿಫಾರಸು ಅಲ್ಲ',
  choose: 'ಈ ಸ್ಥಳ ಆಯ್ಕೆಮಾಡಿ',
  network: 'ಪ್ರಯಾಣದ ಆದ್ಯತೆಗಳು',
  maxWalk: 'ಗರಿಷ್ಠ ನಡಿಗೆ (ಮೀಟರ್)',
  bus: 'ಬಸ್',
  metro: 'ಮೆಟ್ರೋ',
  walk: 'ನಡೆಯಿರಿ',
  timing:
    'ನಕ್ಷೆ ಕೊಂಡಿಗಳು ಅಂದಾಜು; ಸಮೀಕ್ಷಿತ ಮಾರ್ಗಗಳಲ್ಲ. ಸಮಯಗಳು ನಿಗದಿತ ಪರೀಕ್ಷಾ ಮೌಲ್ಯಗಳು.',
  webStatus: 'ಸೇವೆಯ ಸ್ಥಿತಿ',
  retry: 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ',
  remember: 'ಈ ಸಾಧನದಲ್ಲಿ ಉಳಿಸಲಾಗಿದೆ',
  storageSaveFailed:
    'ಎನ್‌ಕ್ರಿಪ್ಟ್ ಮಾಡಿದ ದತ್ತಾಂಶ ಉಳಿಸಲಾಗಲಿಲ್ಲ. ಜಾಗ ಮಾಡಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
  storageReadFailed: 'ಎನ್‌ಕ್ರಿಪ್ಟ್ ಮಾಡಿದ ದತ್ತಾಂಶ ಓದಲಾಗಲಿಲ್ಲ.',
  authValidation:
    'ಮಾನ್ಯ ಇಮೇಲ್ ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ (ಹೊಸ ಖಾತೆಗೆ 8 ಅಥವಾ ಹೆಚ್ಚು ಅಕ್ಷರಗಳು).',
  confirmEmail: 'ಖಾತೆ ದೃಢೀಕರಿಸಲು ಇಮೇಲ್ ಪರಿಶೀಲಿಸಿ, ನಂತರ ಪ್ರವೇಶಿಸಿ.',
  signInFailed: 'ಪ್ರವೇಶ ವಿಫಲವಾಗಿದೆ. ವಿವರಗಳು ಮತ್ತು ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ.',
  signUpFailed: 'ಖಾತೆ ತೆರೆಯಲು ಸಾಧ್ಯವಿಲ್ಲ. ನಮೂನೆ ಮತ್ತು ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ.',
  cacheExpired: 'ಸಂಗ್ರಹಿತ ಪ್ರಯಾಣದ ಅವಧಿ ಮುಗಿದಿದೆ. ಸಂಪರ್ಕಿಸಿ ಮತ್ತೆ ಯೋಜಿಸಿ.',
  restoring: 'ಪ್ರವೇಶ ಮರುಸ್ಥಾಪಿಸಲಾಗುತ್ತಿದೆ',
  preview: 'ಬೆಂಗಳೂರು / ಪ್ರಯಾಣಿಕ ಮುನ್ನೋಟ',
  clearChoices: 'ಒಂದು ಪ್ರಯಾಣ. ಸ್ಪಷ್ಟ ಆಯ್ಕೆಗಳು.',
  modesSummary: 'ಬಸ್ + ಮೆಟ್ರೋ + ನಡಿಗೆ',
  gpsNotice:
    'ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಸ್ಥಳ ಸಂಗ್ರಹಿಸುವುದಿಲ್ಲ. ಜಿಪಿಎಸ್ ಇಲ್ಲದಿರುವುದು ರದ್ದತಿಗೆ ಸಾಕ್ಷಿಯಲ್ಲ.',
  onboardSaveFailed: 'ಆರಂಭಿಕ ಆದ್ಯತೆ ಉಳಿಸಲಾಗಲಿಲ್ಲ.',
  authNotice:
    'ನಿಮ್ಮ Supabase ಖಾತೆ ಬಳಸಿ. ಪಾಸ್‌ವರ್ಡ್ ಆಯ್ದ ದೃಢೀಕರಣ ಸೇವೆಗೆ ಮಾತ್ರ ಕಳುಹಿಸಲಾಗುತ್ತದೆ.',
  webMemory:
    'ವೆಬ್ ಮರುಲೋಡ್ ಮಾಡಿದಾಗ ಪ್ರವೇಶ ಮತ್ತು ದತ್ತಾಂಶ ಅಳಿಯುತ್ತವೆ. ಶಾಶ್ವತ ಎನ್‌ಕ್ರಿಪ್ಟ್ ಆಫ್‌ಲೈನ್ ಸಂಗ್ರಹ ಮೊಬೈಲ್‌ನಲ್ಲಿ ಮಾತ್ರ.',
  backendReady: 'ಬ್ಯಾಕೆಂಡ್ ಸಿದ್ಧ · OTP ಲಭ್ಯತೆಗೆ ಪ್ರಯಾಣ ವಿನಂತಿ ಅಗತ್ಯ',
  backendUnavailable: 'ಬ್ಯಾಕೆಂಡ್ ಲಭ್ಯವಿಲ್ಲ',
  signOutFailed: 'ಪ್ರವೇಶ ಅಳಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
  remove: '{place} ಅಳಿಸಿ',
  savedAt: 'ಉಳಿಸಿದ ಸಮಯ {date}',
  openCached: 'ಸಂಗ್ರಹಿತ ಪ್ರಯಾಣ {number} ತೆರೆಯಿರಿ',
  walkInstruction: 'ನೀಡಿದ ಅಂತ್ಯಬಿಂದುಗಳ ನಡುವೆ ಅಂದಾಜು {distance} ಮೀ ನಡೆಯಿರಿ.',
  boardInstruction:
    '{route} ಹತ್ತಿ; ಪ್ರಯಾಣ {trip}, ದಿಕ್ಕು {direction}. ನೀಡಿದ ಅಂತ್ಯಬಿಂದುವಿನಲ್ಲಿ ಇಳಿಯಿರಿ.',
  unavailable: 'ಲಭ್ಯವಿಲ್ಲ',
  unknown: 'ತಿಳಿದಿಲ್ಲ',
  accessibilityNotice:
    'ಮೂಲ ಪ್ರವೇಶ ಮಾಹಿತಿ ಸ್ಥಿರವಾಗಿದೆ; ನೇರ ಲಿಫ್ಟ್ ಸ್ಥಿತಿ ಮತ್ತು ವಾಹನ ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ. ಈ ಕಲ್ಪಿತ ಜಾಲವನ್ನು ಪ್ರಯಾಣಕ್ಕೆ ಬಳಸಬೇಡಿ.',
  ranking:
    'ಆದ್ಯತೆ: {preference}. ಸೀಮಿತ ಆಯ್ಕೆಗಳು; ಅತ್ಯುತ್ತಮ ಫಲಿತಾಂಶದ ಖಾತರಿಯಿಲ್ಲ. ಎಲ್ಲಾ ಸಮಯ IST.',
  firstPreference: 'ನಿಮ್ಮ ಆದ್ಯತೆಯ ಮೊದಲ ಆಯ್ಕೆ',
  alternative: 'ಪರ್ಯಾಯ',
  syntheticFare: 'ಕಲ್ಪಿತ ದರ',
  initialWait: 'ಆರಂಭಿಕ ಕಾಯುವಿಕೆ',
  minutes: 'ನಿಮಿಷ',
  metres: 'ಮೀ',
  noMatchingStop: 'ಹೊಂದುವ ಕಲ್ಪಿತ ನಿಲ್ದಾಣವಿಲ್ಲ. ರಚಿತ A–D ನಿಲ್ದಾಣಗಳು ಮಾತ್ರ ಲಭ್ಯ.',
  nextJourney: 'ನಿಮ್ಮ ಮುಂದಿನ ಪ್ರಯಾಣ',
  fixtureExample:
    'ಪರೀಕ್ಷಾ ಉದಾಹರಣೆ: 26 ಅಕ್ಟೋಬರ್ 2026, 07:55 IST. 27 ಅಕ್ಟೋಬರ್ ಹಗಲು ಸೇವೆ ಉದ್ದೇಶಪೂರ್ವಕವಾಗಿ ಇಲ್ಲ. ಆಯ್ಕೆ ಸಾಧನದ ಸಮಯ ವಲಯದಲ್ಲಿ; ಫಲಿತಾಂಶ IST ನಲ್ಲಿ.',
  nearbyDistance: '{place} · ನೇರವಾಗಿ ಅಂದಾಜು {distance} ಮೀ',
  nearbyNotice:
    'ರಚಿತ A–D ನಾಲ್ಕು ನಿಲ್ದಾಣ ಮಾತ್ರ ಹುಡುಕಬಹುದು. ಹತ್ತಿರದ ಫಲಿತಾಂಶಗಳು ಕಲ್ಪಿತ ಬಿಂದುಗಳು; ನೈಜ ಸಾರಿಗೆ ಲಭ್ಯತೆಯಲ್ಲ. ಅನುಮತಿಯ ನಂತರ ಸ್ಥಳವನ್ನು ಒಮ್ಮೆ ಮೆಮೊರಿಯಲ್ಲಿ ಬಳಸಲಾಗುತ್ತದೆ.',
  chooseDate: 'ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ',
  chooseTime: 'ಸಮಯ ಆಯ್ಕೆಮಾಡಿ',
  mapOverview: 'ಕಲ್ಪಿತ ಭೌಗೋಳಿಕ ನೋಟ · ಉತ್ತರ ↑',
  mapApproximate: 'ಅಂದಾಜು ಅಂತ್ಯಬಿಂದು ಮಾತ್ರ; ರಸ್ತೆ ಅಥವಾ ಹಳಿ ಮಾರ್ಗವಲ್ಲ.',
  mapEndpoints:
    'ಕಲ್ಪಿತ ಮಾರ್ಗ ಅಂತ್ಯಬಿಂದುಗಳು, ಉತ್ತರ ಮೇಲಕ್ಕೆ. ನಿರ್ದೇಶಾಂಕಗಳು ಕೆಳಗಿವೆ.',
  mapPrivacy:
    'ಐಚ್ಛಿಕ Google ನಕ್ಷೆ ನೋಡಿದ ಪ್ರದೇಶವನ್ನು ಪೂರೈಕೆದಾರರಿಗೆ ಕಳುಹಿಸುತ್ತದೆ. ರೇಖೆಗಳು ಅಂತ್ಯಬಿಂದುಗಳ ಅಂದಾಜು ಸಂಪರ್ಕ; ಮಾರ್ಗ ರೇಖಾಗಣಿತ ನೀಡಿಲ್ಲ.',
  hideMap: 'ನಕ್ಷೆ ಮರೆಮಾಡಿ',
  showMap: 'ಐಚ್ಛಿಕ ನಕ್ಷೆ ತೋರಿಸಿ',
  mapLabel: 'ಭೌಗೋಳಿಕ ನಕ್ಷೆಯ ಮೇಲೆ ಕಲ್ಪಿತ ಪ್ರಯಾಣ',
  mapStep: 'ಕಲ್ಪಿತ ಹಂತ {number}: {mode}',
  mapDestination: 'ಕಲ್ಪಿತ ಗಮ್ಯಸ್ಥಾನ',
  mapUnavailable:
    'ಈ ಬಿಲ್ಡ್‌ನಲ್ಲಿ ನಕ್ಷೆ ಲಭ್ಯವಿಲ್ಲ. Expo Go ಬಳಸಿ, ಅಥವಾ Android Maps SDK ಕೀ ಹೊಂದಿಸಿ ಆ್ಯಪ್ ಅನ್ನು ಮರುನಿರ್ಮಿಸಿ. ಸಂಖ್ಯೆಯ ಚಿತ್ರ ಅಂದಾಜು ಅಂತ್ಯಬಿಂದುಗಳನ್ನು ಮಾತ್ರ ತೋರಿಸುತ್ತದೆ.',
};
export const hi: Record<Key, string> = {
  home: 'योजना',
  saved: 'सहेजे गए',
  settings: 'सेटिंग्स',
  welcome: 'आपकी यात्रा, आसान।',
  continue: 'शुरू करें',
  signIn: 'साइन इन',
  signUp: 'खाता बनाएँ',
  email: 'ईमेल',
  password: 'पासवर्ड',
  origin: 'शुरुआती स्थान',
  destination: 'कहाँ जाना है?',
  plan: 'यात्राएँ खोजें',
  depart: 'प्रस्थान के बाद',
  arrive: 'पहुँचने का समय',
  fastest: 'सबसे तेज़',
  cheapest: 'सबसे सस्ता',
  fewest_transfers: 'कम बदलाव',
  least_walking: 'कम पैदल',
  back: 'वापस',
  simulation: 'सिमुलेशन · काल्पनिक नेटवर्क',
  loading: 'यात्राएँ खोज रहे हैं…',
  language: 'भाषा',
  intro:
    'बस, मेट्रो और पैदल यात्राएँ तुलना करें। यह ऐप काल्पनिक परीक्षण नेटवर्क का उपयोग करता है, बेंगलुरु की लाइव सेवा का नहीं।',
  when: 'समय क्षेत्र सहित तारीख और समय',
  accessible: 'स्रोत के अनुसार व्हीलचेयर सुलभता आवश्यक',
  location: 'आस-पास के स्टॉप खोजें',
  notice: 'निर्धारित परीक्षण समय · लाइव ट्रैकिंग नहीं · सेवा की स्थिति अज्ञात',
  noRoute:
    'इन विकल्पों के लिए यात्रा उपलब्ध नहीं। दूसरा समय, परिवहन साधन या पैदल दूरी सीमा चुनें।',
  offline:
    'इंटरनेट या बैकएंड उपलब्ध नहीं। फिर कोशिश करें या सहेजी यात्रा खोलें।',
  unauthorized: 'आपका सत्र समाप्त है। फिर साइन इन करें।',
  invalid: 'स्थान, समय क्षेत्र सहित समय और पैदल दूरी सीमा जाँचें।',
  incompatible: 'बैकएंड ने असमर्थित उत्तर दिया। अपडेट करें या सहायता लें।',
  denied: 'स्थान उपलब्ध नहीं या अनुमति नहीं मिली। शुरुआती स्थान स्वयं चुनें।',
  noNearby:
    'एक किमी के भीतर कोई काल्पनिक स्टॉप नहीं। यह वास्तविक परिवहन निर्देशिका नहीं है।',
  alternatives: 'आपकी यात्रा के विकल्प',
  detail: 'यात्रा का विवरण',
  unknownFare: 'किराया उपलब्ध नहीं',
  walking: 'पैदल दूरी',
  transfers: 'बदलाव',
  save: 'ऑफ़लाइन सहेजें',
  favorite: 'पसंदीदा गंतव्य',
  clear: 'सहेजा डेटा मिटाएँ',
  signOut: 'साइन आउट करें और डिवाइस डेटा मिटाएँ',
  cache: 'डिवाइस पर एन्क्रिप्टेड यात्रा संग्रह की अनुमति दें (24 घंटे)',
  cacheNotice:
    'सहेजी यात्राओं में स्थान और समय होते हैं। अधिकतम 3 यात्राएँ रखने की अनुमति दें; ऑफ़लाइन लाइव अपडेट नहीं मिलते।',
  empty:
    'अभी कुछ सहेजा नहीं। आपके स्थान और हाल की खोजें इसी डिवाइस पर रहती हैं।',
  stale: 'संग्रहित / पुराना · वर्तमान सुझाव नहीं',
  choose: 'यह स्थान चुनें',
  network: 'यात्रा की प्राथमिकताएँ',
  maxWalk: 'अधिकतम पैदल दूरी (मीटर)',
  bus: 'बस',
  metro: 'मेट्रो',
  walk: 'पैदल चलें',
  timing:
    'नक्शे की कड़ियाँ अनुमानित हैं, सर्वेक्षित रास्ते नहीं। समय निर्धारित परीक्षण मान हैं।',
  webStatus: 'सेवा की स्थिति',
  retry: 'फिर कोशिश करें',
  remember: 'इस डिवाइस पर सहेजा गया',
  storageSaveFailed:
    'एन्क्रिप्टेड डेटा सहेजा नहीं जा सका। जगह खाली करके फिर कोशिश करें।',
  storageReadFailed: 'एन्क्रिप्टेड डेटा पढ़ा नहीं जा सका।',
  authValidation:
    'मान्य ईमेल और पासवर्ड दर्ज करें (नए खाते के लिए कम से कम 8 अक्षर)।',
  confirmEmail: 'खाता पुष्ट करने के लिए ईमेल जाँचें, फिर साइन इन करें।',
  signInFailed: 'साइन इन विफल। विवरण और कनेक्शन जाँचें।',
  signUpFailed: 'खाता नहीं बनाया जा सका। फ़ॉर्म और कनेक्शन जाँचें।',
  cacheExpired: 'संग्रहित यात्रा की अवधि समाप्त है। जुड़कर फिर योजना बनाएँ।',
  restoring: 'सत्र बहाल हो रहा है',
  preview: 'बेंगलुरु / यात्री पूर्वावलोकन',
  clearChoices: 'एक यात्रा। स्पष्ट विकल्प।',
  modesSummary: 'बस + मेट्रो + पैदल',
  gpsNotice:
    'पृष्ठभूमि में स्थान संग्रह नहीं। GPS न मिलना रद्द होने की पुष्टि नहीं है।',
  onboardSaveFailed: 'प्रारंभिक पसंद सहेजी नहीं जा सकी।',
  authNotice:
    'अपना Supabase खाता उपयोग करें। पासवर्ड केवल चुने प्रमाणीकरण प्रदाता को भेजा जाता है।',
  webMemory:
    'वेब रीलोड पर सत्र और डेटा मिटते हैं। स्थायी एन्क्रिप्टेड ऑफ़लाइन संग्रह केवल मोबाइल में है।',
  backendReady: 'बैकएंड तैयार · OTP उपलब्धता के लिए यात्रा अनुरोध आवश्यक',
  backendUnavailable: 'बैकएंड उपलब्ध नहीं',
  signOutFailed: 'सत्र मिटाया नहीं जा सका। फिर कोशिश करें।',
  remove: '{place} हटाएँ',
  savedAt: 'सहेजने का समय {date}',
  openCached: 'संग्रहित यात्रा {number} खोलें',
  walkInstruction: 'दिए अंतिम बिंदुओं के बीच लगभग {distance} मीटर चलें।',
  boardInstruction:
    '{route} पर चढ़ें; ट्रिप {trip}, दिशा {direction}। दिए अंतिम बिंदु पर उतरें।',
  unavailable: 'अनुपलब्ध',
  unknown: 'अज्ञात',
  accessibilityNotice:
    'स्रोत की सुलभता जानकारी स्थिर है; लाइव लिफ्ट स्थिति और वाहन स्थान उपलब्ध नहीं। इस काल्पनिक नेटवर्क से यात्रा न करें।',
  ranking:
    'प्राथमिकता: {preference}। सीमित विकल्प; सर्वोत्तम परिणाम की गारंटी नहीं। सभी समय IST हैं।',
  firstPreference: 'आपकी प्राथमिकता का पहला विकल्प',
  alternative: 'विकल्प',
  syntheticFare: 'काल्पनिक किराया',
  initialWait: 'शुरुआती प्रतीक्षा',
  minutes: 'मिनट',
  metres: 'मीटर',
  noMatchingStop:
    'कोई मेल खाता काल्पनिक स्टॉप नहीं। केवल रचित A–D स्टॉप उपलब्ध हैं।',
  nextJourney: 'आपकी अगली यात्रा',
  fixtureExample:
    'परीक्षण उदाहरण: 26 अक्टूबर 2026, 07:55 IST। 27 अक्टूबर को जानबूझकर दिन की सेवा नहीं। चयन डिवाइस के समय क्षेत्र में; परिणाम IST में हैं।',
  nearbyDistance: '{place} · सीधी रेखा में लगभग {distance} मीटर',
  nearbyNotice:
    'केवल रचित A–D चार स्टॉप खोजे जा सकते हैं। पास के परिणाम काल्पनिक बिंदु हैं, वास्तविक परिवहन उपलब्धता नहीं। अनुमति के बाद स्थान एक बार मेमोरी में उपयोग होता है।',
  chooseDate: 'तारीख चुनें',
  chooseTime: 'समय चुनें',
  mapOverview: 'काल्पनिक भौगोलिक दृश्य · उत्तर ↑',
  mapApproximate: 'केवल अनुमानित अंतिम बिंदु; सड़क या रेल रास्ता नहीं।',
  mapEndpoints:
    'काल्पनिक मार्ग के अंतिम बिंदु, उत्तर ऊपर। निर्देशांक नीचे हैं।',
  mapPrivacy:
    'वैकल्पिक Google नक्शा देखे क्षेत्र को प्रदाता को भेजता है। रेखाएँ अंतिम बिंदुओं का अनुमानित जोड़ हैं; मार्ग ज्यामिति नहीं मिली।',
  hideMap: 'नक्शा छिपाएँ',
  showMap: 'वैकल्पिक नक्शा दिखाएँ',
  mapLabel: 'भौगोलिक नक्शे पर काल्पनिक यात्रा',
  mapStep: 'काल्पनिक चरण {number}: {mode}',
  mapDestination: 'काल्पनिक गंतव्य',
  mapUnavailable:
    'इस बिल्ड में नक्शा उपलब्ध नहीं। Expo Go उपयोग करें, या Android Maps SDK कुंजी जोड़कर ऐप दोबारा बनाएँ। क्रमांक वाला चित्र केवल अनुमानित अंतिम बिंदु दिखाता है।',
};
export const dictionaries = { en, kn, hi };
// Partial overrides allow explicit fallback tests and future incomplete locale packs.
export function translator(
  language: Language,
  overrides?: Partial<Record<Key, string>>,
) {
  const dictionary: Partial<Record<Key, string>> =
    overrides ?? dictionaries[language];
  return (key: Key, values: Record<string, string | number> = {}): string => {
    const template = dictionary[key]?.trim() ? dictionary[key]! : en[key];
    return template.replace(/\{(\w+)\}/g, (match, name: string) =>
      String(values[name] ?? match),
    );
  };
}
export type Translate = ReturnType<typeof translator>;
