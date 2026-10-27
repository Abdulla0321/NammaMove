import React, { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  BackHandler,
  Platform,
  ScrollView,
  Switch,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { ClientError } from './src/api';
import { fixtureStops, nearbyPlaces, searchPlaces } from './src/fixtures';
import { translator, type Language } from './src/i18n';
import {
  cacheJourney,
  cacheValid,
  libraryKey,
  loadLibrary,
} from './src/library';
import RouteMap from './src/RouteMap';
import { createServices, type Services } from './src/services';
import TimePicker from './src/TimePicker';
import {
  emptyLibrary,
  type CachedJourney,
  type Itinerary,
  type Library,
  type Place,
  type PlanRequest,
  type PlanResponse,
  type Session,
} from './src/types';
import { Button, Chip, colors, Field, Notice, styles } from './src/ui';

type Tab = 'home' | 'saved' | 'settings';
type Result = {
  response: PlanResponse;
  request: PlanRequest;
  savedAt?: string;
};
const preferences = [
  'fastest',
  'cheapest',
  'fewest_transfers',
  'least_walking',
] as const;
const time = (value: string) =>
  new Date(value).toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

export default function App({
  services: supplied,
}: { services?: Services } = {}) {
  const [runtime] = useState(() => {
    try {
      return { services: supplied ?? createServices(), error: '' };
    } catch {
      return {
        services: undefined,
        error:
          'Configure the public API and Supabase environment values, then restart Expo. Never add server secrets to the app.',
      };
    }
  });
  return (
    <SafeAreaProvider>
      {runtime.services ? (
        <CommuterApp services={runtime.services} />
      ) : (
        <SafeAreaView style={styles.root}>
          <View style={styles.content}>
            <Text style={styles.brand}>NammaMove</Text>
            <Notice error>{runtime.error}</Notice>
          </View>
        </SafeAreaView>
      )}
    </SafeAreaProvider>
  );
}

export function CommuterApp({ services }: { services: Services }) {
  const [language, setLanguage] = useState<Language>('en');
  const t = translator(language);
  const { width } = useWindowDimensions();
  const [onboarded, setOnboarded] = useState(false);
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [tab, setTab] = useState<Tab>('home');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [origin, setOrigin] = useState<Place>(fixtureStops[0]!);
  const [destination, setDestination] = useState<Place>(fixtureStops[3]!);
  const [picker, setPicker] = useState<'origin' | 'destination' | null>(null);
  const [search, setSearch] = useState('');
  const [when, setWhen] = useState('2026-10-26T07:55:00+05:30');
  const [arriveBy, setArriveBy] = useState(false);
  const [preference, setPreference] =
    useState<(typeof preferences)[number]>('fastest');
  const [wheelchair, setWheelchair] = useState(true);
  const [modes, setModes] = useState<('BUS' | 'SUBWAY')[]>(['BUS', 'SUBWAY']);
  const [walkLimit, setWalkLimit] = useState('500');
  const [result, setResult] = useState<Result | null>(null);
  const [detail, setDetail] = useState<Itinerary | null>(null);
  const [library, setLibrary] = useState<Library>(emptyLibrary);
  const [libraryReady, setLibraryReady] = useState(false);
  const [nearby, setNearby] = useState<(Place & { distance: number })[] | null>(
    null,
  );
  const [serviceStatus, setServiceStatus] = useState('');
  const generation = useRef(0);
  const sessionUser = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    let active = true;
    const changeSession = (value: Session | null) => {
      if (!active) return;
      if (sessionUser.current === (value?.userId ?? null)) return;
      sessionUser.current = value?.userId ?? null;
      generation.current++;
      setSession(value);
      setResult(null);
      setDetail(null);
      setNearby(null);
      setLibrary(emptyLibrary());
      setLibraryReady(false);
      setBusy(false);
    };
    const unsubscribe = services.auth.subscribe(changeSession);
    void Promise.all([
      services.auth.session(),
      services.store.getItem('nammamove.onboarded'),
    ])
      .then(([value, onboard]) => {
        if (active) {
          changeSession(value);
          setOnboarded(onboard === 'yes');
          setReady(true);
        }
      })
      .catch(() => {
        if (active) {
          setReady(true);
          setMessage(t('offline'));
        }
      });
    return () => {
      active = false;
      // This is a request-generation counter, not a rendered node reference.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      generation.current++;
      unsubscribe();
    };
    // Runtime is fixed for this app instance; translated messages are not auth dependencies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [services]);

  useEffect(() => {
    let active = true;
    if (session)
      void loadLibrary(services.store, session.userId)
        .then((value) => {
          if (active) {
            setLibrary(value);
            setLibraryReady(true);
          }
        })
        .catch(() => {
          if (active) setMessage('Could not read encrypted device storage.');
        });
    return () => {
      active = false;
    };
  }, [session, services]);

  useEffect(() => {
    const subscription = BackHandler.addEventListener(
      'hardwareBackPress',
      () => {
        if (detail) {
          setDetail(null);
          return true;
        }
        if (result) {
          setResult(null);
          return true;
        }
        if (picker) {
          setPicker(null);
          return true;
        }
        if (tab !== 'home') {
          setTab('home');
          return true;
        }
        return false;
      },
    );
    return () => subscription.remove();
  }, [detail, result, picker, tab]);

  async function persist(next: Library) {
    if (!session || !libraryReady) return;
    setLibrary(next);
    try {
      await services.store.setItem(
        libraryKey(session.userId),
        JSON.stringify(next),
      );
    } catch {
      setMessage(
        'Could not save encrypted device data. Free storage and retry.',
      );
    }
  }
  async function authenticate(signUp = false) {
    setMessage('');
    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ||
      !password ||
      (signUp && password.length < 8)
    ) {
      setMessage(
        'Enter a valid email and password (8+ characters for a new account).',
      );
      return;
    }
    setBusy(true);
    try {
      if (signUp) {
        const signedIn = await services.auth.signUp(email.trim(), password);
        if (!signedIn)
          setMessage('Check your email to confirm your account, then sign in.');
      } else await services.auth.signIn(email.trim(), password);
      setPassword('');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t('offline'));
    } finally {
      setBusy(false);
    }
  }
  async function plan() {
    setMessage('');
    if (
      !/[zZ]$|[+-]\d{2}:\d{2}$/.test(when) ||
      !Number.isFinite(Date.parse(when)) ||
      !/^\d+$/.test(walkLimit) ||
      +walkLimit > 10000 ||
      !modes.length ||
      origin.id === destination.id
    ) {
      setMessage(t('invalid'));
      return;
    }
    const current = ++generation.current;
    const request: PlanRequest = {
      origin: origin.point,
      destination: destination.point,
      when,
      arrive_by: arriveBy,
      preference,
      modes: [...modes, 'WALK'],
      max_walk_m: +walkLimit,
      max_transfers: 3,
      wheelchair,
      transit_required: true,
      limit: 5,
    };
    setBusy(true);
    setDetail(null);
    setResult(null);
    try {
      const response = await services.plan(request);
      if (current !== generation.current) return;
      setResult({ request, response });
      AccessibilityInfo.announceForAccessibility(
        response.status === 'no_route' ? t('noRoute') : t('alternatives'),
      );
      await persist({
        ...library,
        recent: [
          { origin, destination, when },
          ...library.recent.filter(
            (r) =>
              r.origin.id !== origin.id || r.destination.id !== destination.id,
          ),
        ].slice(0, 5),
      });
    } catch (error) {
      if (current !== generation.current) return;
      setMessage(t(error instanceof ClientError ? error.code : 'offline'));
      if (error instanceof ClientError && error.code === 'unauthorized') {
        sessionUser.current = null;
        setSession(null);
        setResult(null);
        setLibrary(emptyLibrary());
      }
    } finally {
      if (current === generation.current) setBusy(false);
    }
  }
  async function locate() {
    setMessage('');
    setBusy(true);
    const current = generation.current;
    try {
      const coordinates = await services.locate();
      if (current !== generation.current) return;
      const places = nearbyPlaces(coordinates.latitude, coordinates.longitude);
      setNearby(places);
      if (!places.length) setMessage(t('noNearby'));
    } catch {
      if (current === generation.current) setMessage(t('denied'));
    } finally {
      if (current === generation.current) setBusy(false);
    }
  }
  async function saveJourney() {
    if (!result || !library.cacheEnabled) {
      setMessage(t('cacheNotice'));
      return;
    }
    await persist(
      cacheJourney(library, {
        savedAt: new Date().toISOString(),
        request: result.request,
        response: result.response,
      }),
    );
    setMessage(t('remember'));
  }
  function openCached(item: CachedJourney) {
    if (!cacheValid(item.savedAt)) {
      setMessage('This cached journey has expired. Reconnect and plan again.');
      return;
    }
    setResult({ ...item });
    setDetail(null);
    setTab('home');
    setMessage('');
  }
  function navigate(next: Tab) {
    generation.current++;
    setBusy(false);
    setTab(next);
    setDetail(null);
    setResult(null);
    setPicker(null);
    setMessage('');
  }

  const notice = (
    <>
      <Text style={styles.eyebrow}>{t('simulation')}</Text>
      <Text style={styles.muted}>{t('notice')}</Text>
    </>
  );
  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Text style={styles.brand}>
          namma<Text style={{ color: colors.ink }}>move</Text>
          <Text style={{ color: colors.green }}> ↗</Text>
        </Text>
        {notice}
      </View>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.content}
      >
        {!ready ? (
          <ActivityIndicator
            accessibilityLabel="Restoring session"
            color={colors.green}
          />
        ) : !onboarded ? (
          <>
            <Text style={styles.eyebrow}>BENGALURU / COMMUTER PREVIEW</Text>
            <Text accessibilityRole="header" style={styles.title}>
              {t('welcome')}
            </Text>
            <Text style={styles.body}>{t('intro')}</Text>
            <View style={styles.card}>
              <Text style={styles.heading}>One journey. Clear choices.</Text>
              <Text style={styles.body}>Bus + Metro + Walk</Text>
              <Text style={styles.muted}>
                No background location collection. Missing GPS never confirms
                cancellation.
              </Text>
            </View>
            <View style={styles.row}>
              {(['en', 'kn', 'hi'] as const).map((lang) => (
                <Chip
                  key={lang}
                  title={{ en: 'English', kn: 'ಕನ್ನಡ', hi: 'हिन्दी' }[lang]}
                  selected={language === lang}
                  onPress={() => setLanguage(lang)}
                />
              ))}
            </View>
            <Button
              title={t('continue')}
              onPress={() => {
                setOnboarded(true);
                void services.store
                  .setItem('nammamove.onboarded', 'yes')
                  .catch(() =>
                    setMessage('Onboarding preference could not be saved.'),
                  );
              }}
            />
          </>
        ) : !session ? (
          <>
            <Text accessibilityRole="header" style={styles.title}>
              {t('signIn')}
            </Text>
            <Text style={styles.body}>
              Use your Supabase account. Your password is sent only to your
              configured Auth provider.
            </Text>
            <Field
              label={t('email')}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
            />
            <Field
              label={t('password')}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="current-password"
            />
            <Button
              title={t('signIn')}
              disabled={busy}
              onPress={() => void authenticate()}
            />
            <Button
              title={t('signUp')}
              disabled={busy}
              secondary
              onPress={() => void authenticate(true)}
            />
          </>
        ) : tab === 'settings' ? (
          <>
            <Text accessibilityRole="header" style={styles.title}>
              {t('settings')}
            </Text>
            <Text style={styles.label}>{t('language')}</Text>
            <View style={styles.row}>
              {(['en', 'kn', 'hi'] as const).map((lang) => (
                <Chip
                  key={lang}
                  title={{ en: 'English', kn: 'ಕನ್ನಡ', hi: 'हिन्दी' }[lang]}
                  selected={language === lang}
                  onPress={() => setLanguage(lang)}
                />
              ))}
            </View>
            <Text style={styles.body}>{t('cacheNotice')}</Text>
            <View style={styles.row}>
              <Switch
                accessibilityLabel={t('cache')}
                value={library.cacheEnabled}
                disabled={!libraryReady}
                onValueChange={(cacheEnabled) =>
                  void persist({
                    ...library,
                    cacheEnabled,
                    journeys: cacheEnabled ? library.journeys : [],
                  })
                }
              />
              <Text style={[styles.body, { flex: 1 }]}>{t('cache')}</Text>
            </View>
            {Platform.OS === 'web' && (
              <Notice>
                Web preview uses memory only: sessions and saved data are
                cleared on reload. Persistent encrypted offline storage is
                native-only.
              </Notice>
            )}
            <Button
              title={t('clear')}
              secondary
              onPress={() => void persist(emptyLibrary())}
            />
            <Button
              title={t('webStatus')}
              secondary
              onPress={() => {
                void services
                  .health()
                  .then((ok) =>
                    setServiceStatus(
                      ok
                        ? 'Backend ready · OTP availability requires a journey request'
                        : 'Backend unavailable',
                    ),
                  );
              }}
            />
            {!!serviceStatus && (
              <Text accessibilityLiveRegion="polite" style={styles.body}>
                {serviceStatus}
              </Text>
            )}
            <Button
              title={t('signOut')}
              onPress={() => {
                if (session)
                  void services.store
                    .removeItem(libraryKey(session.userId))
                    .then(() => services.auth.signOut())
                    .then(() => {
                      setSession(null);
                      setLibrary(emptyLibrary());
                      setResult(null);
                    })
                    .catch(() =>
                      setMessage('Could not clear this session. Retry.'),
                    );
              }}
            />
          </>
        ) : tab === 'saved' ? (
          <>
            <Text accessibilityRole="header" style={styles.title}>
              {t('saved')}
            </Text>
            {!library.favorites.length &&
              !library.recent.length &&
              !library.journeys.length && (
                <Text style={styles.body}>{t('empty')}</Text>
              )}
            {library.favorites.map((place) => (
              <View key={place.id} style={styles.card}>
                <Button
                  title={place.name}
                  secondary
                  onPress={() => {
                    setDestination(place);
                    navigate('home');
                  }}
                />
                <Button
                  title={`Remove ${place.name}`}
                  secondary
                  onPress={() =>
                    void persist({
                      ...library,
                      favorites: library.favorites.filter(
                        (p) => p.id !== place.id,
                      ),
                    })
                  }
                />
              </View>
            ))}
            {library.recent.map((recent, i) => (
              <Button
                key={i}
                title={`${recent.origin.id} → ${recent.destination.id} · ${recent.when}`}
                secondary
                onPress={() => {
                  setOrigin(recent.origin);
                  setDestination(recent.destination);
                  setWhen(recent.when);
                  navigate('home');
                }}
              />
            ))}
            {library.journeys
              .filter((j) => cacheValid(j.savedAt))
              .map((item, i) => (
                <View key={i} style={styles.card}>
                  <Text style={styles.label}>{t('stale')}</Text>
                  <Text style={styles.muted}>
                    Saved {new Date(item.savedAt).toLocaleString()}
                  </Text>
                  <Button
                    title={`Open cached journey ${i + 1}`}
                    secondary
                    onPress={() => openCached(item)}
                  />
                </View>
              ))}
          </>
        ) : detail && result ? (
          <>
            <Button
              title={t('back')}
              secondary
              onPress={() => setDetail(null)}
            />
            <Text accessibilityRole="header" style={styles.title}>
              {t('detail')}
            </Text>
            {result.savedAt && (
              <Notice>
                {t('stale')} · {result.savedAt}
              </Notice>
            )}
            <RouteMap itinerary={detail} enabled={services.mapEnabled} />
            <Text style={styles.body}>{t('timing')}</Text>
            {detail.legs.map((leg, i) => (
              <View key={i} style={styles.card}>
                <Text accessibilityRole="header" style={styles.heading}>
                  {i + 1}.{' '}
                  {leg.mode === 'WALK'
                    ? t('walk')
                    : leg.mode === 'BUS'
                      ? t('bus')
                      : t('metro')}
                </Text>
                <Text style={styles.body}>
                  {time(leg.start)} → {time(leg.end)} IST
                </Text>
                <Text style={styles.muted}>
                  {leg.mode === 'WALK'
                    ? `Walk approximately ${Math.round(leg.distance_m)} m between the listed endpoints.`
                    : `Board ${leg.route_id ?? leg.mode}; trip ${leg.trip_id ?? 'unavailable'}, direction ${leg.direction_id ?? 'unknown'}. Alight at the listed endpoint.`}
                </Text>
                <Text style={styles.muted}>
                  {leg.from_lat.toFixed(4)}, {leg.from_lon.toFixed(4)} →{' '}
                  {leg.to_lat.toFixed(4)}, {leg.to_lon.toFixed(4)}
                </Text>
              </View>
            ))}
            {detail.explanations.map((explanation, i) => (
              <Text key={i} style={styles.muted}>
                {explanation}
              </Text>
            ))}
            <Notice>
              Source accessibility is static; live lifts and vehicle positions
              are unavailable. Do not use this invented network for travel.
            </Notice>
          </>
        ) : result ? (
          <>
            <Button
              title={t('back')}
              secondary
              onPress={() => setResult(null)}
            />
            <Text accessibilityRole="header" style={styles.title}>
              {t('alternatives')}
            </Text>
            {result.savedAt && (
              <Notice>
                {t('stale')} · {result.savedAt}
              </Notice>
            )}
            <Text style={styles.muted}>
              Ranking: {result.response.preference}. Bounded candidates; no
              global optimum guarantee. All times IST.
            </Text>
            {result.response.status === 'no_route' ? (
              <Notice>{t('noRoute')}</Notice>
            ) : (
              result.response.itineraries.map((journey, i) => (
                <View key={i} style={styles.card}>
                  <Text style={styles.eyebrow}>
                    {i === 0 ? 'FIRST FOR YOUR PREFERENCE' : 'ALTERNATIVE'} ·
                    SIMULATION
                  </Text>
                  <Text style={styles.heading}>
                    {Math.round(journey.duration_seconds / 60)} min ·{' '}
                    {time(journey.start)}–{time(journey.end)}
                  </Text>
                  <Text style={styles.body}>
                    {journey.legs.map((leg) => leg.mode).join(' → ')}
                  </Text>
                  <Text style={styles.body}>
                    {journey.fare_inr === null
                      ? t('unknownFare')
                      : `₹${journey.fare_inr} · synthetic fare`}{' '}
                    · {journey.transfers} {t('transfers')}
                  </Text>
                  <Text style={styles.muted}>
                    {t('walking')}: {Math.round(journey.walking_m)} m · Initial
                    wait: {Math.round(journey.initial_wait_seconds / 60)} min
                  </Text>
                  <Button
                    title={`${t('detail')} ${i + 1}`}
                    onPress={() => setDetail(journey)}
                  />
                </View>
              ))
            )}
            <Text style={styles.muted}>
              {result.response.source_attribution}
            </Text>
            {result.response.status === 'ok' && !result.savedAt && (
              <Button
                title={t('save')}
                secondary
                onPress={() => void saveJourney()}
              />
            )}
          </>
        ) : picker ? (
          <>
            <Button
              title={t('back')}
              secondary
              onPress={() => setPicker(null)}
            />
            <Field
              label={picker === 'origin' ? t('origin') : t('destination')}
              value={search}
              onChangeText={setSearch}
              autoFocus
            />
            {searchPlaces(search).map((place) => (
              <Button
                key={place.id}
                title={place.name}
                secondary
                onPress={() => {
                  if (picker === 'origin') setOrigin(place);
                  else setDestination(place);
                  setPicker(null);
                }}
              />
            ))}
            {!searchPlaces(search).length && (
              <Text style={styles.body}>
                No matching synthetic stop. Only authored stops A–D are
                available.
              </Text>
            )}
          </>
        ) : (
          <>
            <Text style={styles.eyebrow}>YOUR NEXT JOURNEY</Text>
            <Text accessibilityRole="header" style={styles.title}>
              {t('welcome')}
            </Text>
            <View style={styles.card}>
              <Text style={styles.label}>{t('origin')}</Text>
              <Button
                title={origin.name}
                secondary
                onPress={() => {
                  setPicker('origin');
                  setSearch('');
                }}
              />
              <Text style={styles.label}>{t('destination')}</Text>
              <Button
                title={destination.name}
                secondary
                onPress={() => {
                  setPicker('destination');
                  setSearch('');
                }}
              />
              <View style={styles.row}>
                <Chip
                  title={t('depart')}
                  selected={!arriveBy}
                  onPress={() => setArriveBy(false)}
                />
                <Chip
                  title={t('arrive')}
                  selected={arriveBy}
                  onPress={() => setArriveBy(true)}
                />
              </View>
              <TimePicker value={when} onChange={setWhen} label={t('when')} />
              <Text style={styles.muted}>
                Fixture example: 26 Oct 2026, 07:55 IST. Date 27 Oct has no
                daytime service by design. Native picker uses your device
                timezone; results show IST.
              </Text>
            </View>
            <Text accessibilityRole="header" style={styles.heading}>
              {t('network')}
            </Text>
            <View style={styles.row}>
              {preferences.map((pref) => (
                <Chip
                  key={pref}
                  title={t(pref)}
                  selected={preference === pref}
                  onPress={() => setPreference(pref)}
                />
              ))}
            </View>
            <View style={styles.row}>
              {(['BUS', 'SUBWAY'] as const).map((mode) => (
                <Chip
                  key={mode}
                  title={mode === 'BUS' ? t('bus') : t('metro')}
                  selected={modes.includes(mode)}
                  onPress={() =>
                    setModes(
                      modes.includes(mode)
                        ? modes.filter((m) => m !== mode)
                        : [...modes, mode],
                    )
                  }
                />
              ))}
            </View>
            <Field
              label={t('maxWalk')}
              value={walkLimit}
              onChangeText={setWalkLimit}
              keyboardType="number-pad"
            />
            <View style={styles.row}>
              <Switch
                accessibilityLabel={t('accessible')}
                value={wheelchair}
                onValueChange={setWheelchair}
              />
              <Text style={[styles.body, { flex: 1 }]}>{t('accessible')}</Text>
            </View>
            <Button
              title={t('plan')}
              disabled={busy || !libraryReady}
              onPress={() => void plan()}
            />
            <View
              style={[
                styles.row,
                width < 380 && {
                  flexDirection: 'column',
                  alignItems: 'stretch',
                },
              ]}
            >
              <Button
                title={t('location')}
                disabled={busy}
                secondary
                onPress={() => void locate()}
              />
              <Button
                title={t('favorite')}
                disabled={!libraryReady}
                secondary
                onPress={() =>
                  void persist({
                    ...library,
                    favorites: [
                      destination,
                      ...library.favorites.filter(
                        (p) => p.id !== destination.id,
                      ),
                    ].slice(0, 10),
                  })
                }
              />
            </View>
            {nearby?.map((place) => (
              <Button
                key={place.id}
                title={`${place.name} · approximately ${Math.round(place.distance)} m straight-line`}
                secondary
                onPress={() =>
                  setOrigin(fixtureStops.find((stop) => stop.id === place.id)!)
                }
              />
            ))}
            <Notice>
              Only the four authored stops A–D are searchable. Nearby results
              are synthetic endpoints, not real transport availability. Location
              is used once, in memory, after permission.
            </Notice>
          </>
        )}
        {busy && (
          <View
            accessible
            accessibilityRole="progressbar"
            accessibilityLabel={t('loading')}
            style={styles.card}
          >
            <Text style={styles.body}>{t('loading')}</Text>
            <View style={styles.skeleton} />
            <View style={[styles.skeleton, { width: '70%' }]} />
          </View>
        )}
        {!!message && <Notice error>{message}</Notice>}
      </ScrollView>
      {session && onboarded && (
        <View style={styles.nav}>
          {(['home', 'saved', 'settings'] as const).map((item) => (
            <Chip
              key={item}
              title={t(item)}
              selected={tab === item}
              onPress={() => navigate(item)}
            />
          ))}
        </View>
      )}
    </SafeAreaView>
  );
}
