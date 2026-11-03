import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  const t = useMemo(() => translator(language), [language]);
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
          if (active) setMessage(t('storageReadFailed'));
        });
    return () => {
      active = false;
    };
  }, [session, services, t]);

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
    if (!session || !libraryReady) return false;
    const userId = session.userId;
    const current = generation.current;
    try {
      await services.store.setItem(libraryKey(userId), JSON.stringify(next));
      if (current !== generation.current || sessionUser.current !== userId)
        return false;
      setLibrary(next);
      return true;
    } catch {
      if (current === generation.current) setMessage(t('storageSaveFailed'));
      return false;
    }
  }
  async function authenticate(signUp = false) {
    setMessage('');
    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ||
      !password ||
      (signUp && password.length < 8)
    ) {
      setMessage(t('authValidation'));
      return;
    }
    setBusy(true);
    try {
      if (signUp) {
        const signedIn = await services.auth.signUp(email.trim(), password);
        if (!signedIn) setMessage(t('confirmEmail'));
      } else await services.auth.signIn(email.trim(), password);
      setPassword('');
    } catch {
      setMessage(t(signUp ? 'signUpFailed' : 'signInFailed'));
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
    const saved = await persist(
      cacheJourney(library, {
        savedAt: new Date().toISOString(),
        request: result.request,
        response: result.response,
      }),
    );
    if (saved) setMessage(t('remember'));
  }
  function openCached(item: CachedJourney) {
    if (!cacheValid(item.savedAt)) {
      setMessage(t('cacheExpired'));
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
            accessibilityLabel={t('restoring')}
            color={colors.green}
          />
        ) : !onboarded ? (
          <>
            <Text style={styles.eyebrow}>{t('preview')}</Text>
            <Text accessibilityRole="header" style={styles.title}>
              {t('welcome')}
            </Text>
            <Text style={styles.body}>{t('intro')}</Text>
            <View style={styles.card}>
              <Text style={styles.heading}>{t('clearChoices')}</Text>
              <Text style={styles.body}>{t('modesSummary')}</Text>
              <Text style={styles.muted}>{t('gpsNotice')}</Text>
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
                  .catch(() => setMessage(t('onboardSaveFailed')));
              }}
            />
          </>
        ) : !session ? (
          <>
            <Text accessibilityRole="header" style={styles.title}>
              {t('signIn')}
            </Text>
            <Text style={styles.body}>{t('authNotice')}</Text>
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
            {Platform.OS === 'web' && <Notice>{t('webMemory')}</Notice>}
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
                      ok ? t('backendReady') : t('backendUnavailable'),
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
                    .catch(() => setMessage(t('signOutFailed')));
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
                  title={t('remove', { place: place.name })}
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
                    {t('savedAt', {
                      date: new Date(item.savedAt).toLocaleString(
                        language === 'en' ? 'en-IN' : `${language}-IN`,
                      ),
                    })}
                  </Text>
                  <Button
                    title={t('openCached', { number: i + 1 })}
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
            <RouteMap itinerary={detail} enabled={services.mapEnabled} t={t} />
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
                    ? t('walkInstruction', {
                        distance: Math.round(leg.distance_m),
                      })
                    : t('boardInstruction', {
                        route: leg.route_id ?? leg.mode,
                        trip: leg.trip_id ?? t('unavailable'),
                        direction: leg.direction_id ?? t('unknown'),
                      })}
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
            <Notice>{t('accessibilityNotice')}</Notice>
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
              {t('ranking', {
                preference: t(
                  preferences.find((p) => p === result.response.preference) ??
                    preference,
                ),
              })}
            </Text>
            {result.response.status === 'no_route' ? (
              <Notice>{t('noRoute')}</Notice>
            ) : (
              result.response.itineraries.map((journey, i) => (
                <View key={i} style={styles.card}>
                  <Text style={styles.eyebrow}>
                    {i === 0 ? t('firstPreference') : t('alternative')} ·{' '}
                    {t('simulation')}
                  </Text>
                  <Text style={styles.heading}>
                    {Math.round(journey.duration_seconds / 60)} {t('minutes')} ·{' '}
                    {time(journey.start)}–{time(journey.end)}
                  </Text>
                  <Text style={styles.body}>
                    {journey.legs
                      .map((leg) =>
                        t(
                          leg.mode === 'BUS'
                            ? 'bus'
                            : leg.mode === 'WALK'
                              ? 'walk'
                              : 'metro',
                        ),
                      )
                      .join(' → ')}
                  </Text>
                  <Text style={styles.body}>
                    {journey.fare_inr === null
                      ? t('unknownFare')
                      : `₹${journey.fare_inr} · ${t('syntheticFare')}`}{' '}
                    · {journey.transfers} {t('transfers')}
                  </Text>
                  <Text style={styles.muted}>
                    {t('walking')}: {Math.round(journey.walking_m)}{' '}
                    {t('metres')} · {t('initialWait')}:{' '}
                    {Math.round(journey.initial_wait_seconds / 60)}{' '}
                    {t('minutes')}
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
              <Text style={styles.body}>{t('noMatchingStop')}</Text>
            )}
          </>
        ) : (
          <>
            <Text style={styles.eyebrow}>{t('nextJourney')}</Text>
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
              <TimePicker
                value={when}
                onChange={setWhen}
                label={t('when')}
                t={t}
              />
              <Text style={styles.muted}>{t('fixtureExample')}</Text>
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
                title={t('nearbyDistance', {
                  place: place.name,
                  distance: Math.round(place.distance),
                })}
                secondary
                onPress={() =>
                  setOrigin(fixtureStops.find((stop) => stop.id === place.id)!)
                }
              />
            ))}
            <Notice>{t('nearbyNotice')}</Notice>
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
