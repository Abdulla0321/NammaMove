import fixture from './fixtures/plan.json';
import { apiClient, ClientError } from '../src/api';
import {
  cacheJourney,
  cacheValid,
  loadLibrary,
  libraryKey,
} from '../src/library';
import { chunkedStore, memoryStore } from '../src/storage';
import { emptyLibrary, type PlanRequest } from '../src/types';
import { parsePlan } from '../src/validation';
import { fixtureStops, nearbyPlaces, searchPlaces } from '../src/fixtures';
import { translator } from '../src/i18n';

const request: PlanRequest = {
  origin: { stop_id: 'A' },
  destination: { stop_id: 'D' },
  when: '2026-10-26T07:55:00+05:30',
  arrive_by: false,
  preference: 'fastest',
  modes: ['BUS', 'SUBWAY', 'WALK'],
  max_walk_m: 500,
  max_transfers: 3,
  wheelchair: true,
  transit_required: true,
  limit: 5,
};
const response = (status: number, value: unknown = fixture) =>
  ({
    status,
    ok: status >= 200 && status < 300,
    text: async () => JSON.stringify(value),
  }) as Response;

test('authenticated request matches existing routing contract and labels', async () => {
  const fetcher = jest.fn().mockResolvedValue(response(200));
  const client = apiClient(
    'https://api.example',
    { token: async () => 'token', refresh: async () => null },
    fetcher,
  );
  const result = await client.plan(request);
  expect(result.data_mode).toBe('simulation');
  expect(result.itineraries[0]?.fare_inr).toBe(30);
  expect(fetcher.mock.calls[0]?.[1].headers.Authorization).toBe('Bearer token');
  expect(JSON.parse(fetcher.mock.calls[0]?.[1].body)).toEqual(request);
});
test('expired access token refreshes exactly once then retries', async () => {
  const fetcher = jest
    .fn()
    .mockResolvedValueOnce(response(401))
    .mockResolvedValueOnce(response(200));
  const refresh = jest.fn().mockResolvedValue('new');
  await apiClient(
    'https://api.example',
    { token: async () => 'old', refresh },
    fetcher,
  ).plan(request);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[1]?.[1].headers.Authorization).toBe('Bearer new');
});
test('rejected refresh fails closed without a retry loop', async () => {
  const fetcher = jest.fn().mockResolvedValue(response(401));
  await expect(
    apiClient(
      'https://api.example',
      { token: async () => 'old', refresh: async () => null },
      fetcher,
    ).plan(request),
  ).rejects.toEqual(new ClientError('unauthorized'));
  expect(fetcher).toHaveBeenCalledTimes(1);
});
test.each([
  [422, 'invalid'],
  [409, 'invalid'],
  [503, 'offline'],
  [403, 'unauthorized'],
] as const)('HTTP %s becomes meaningful client state', async (status, code) => {
  await expect(
    apiClient(
      'https://api.example',
      { token: async () => 'token', refresh: async () => null },
      jest.fn().mockResolvedValue(response(status)),
    ).plan(request),
  ).rejects.toEqual(new ClientError(code));
});
test('network failure is not a cancellation and does not fabricate a result', async () => {
  await expect(
    apiClient(
      'https://api.example',
      { token: async () => 'token', refresh: async () => null },
      jest.fn().mockRejectedValue(new Error('network')),
    ).plan(request),
  ).rejects.toEqual(new ClientError('offline'));
});
test('unexpected live labels and malformed legs fail contract validation', () => {
  expect(() => parsePlan({ ...fixture, data_mode: 'live' })).toThrow();
  const bad = JSON.parse(JSON.stringify(fixture));
  bad.itineraries[0].legs[0].end = '2020-01-01T00:00:00Z';
  expect(() => parsePlan(bad)).toThrow();
});
test('unknown fare remains null and no-route has no invented alternatives', () => {
  const value = JSON.parse(JSON.stringify(fixture));
  value.itineraries[0].fare_inr = null;
  value.itineraries[0].fare_status = 'unknown';
  expect(parsePlan(value).itineraries[0]?.fare_inr).toBeNull();
  expect(
    parsePlan({ ...fixture, status: 'no_route', itineraries: [] }).itineraries,
  ).toEqual([]);
});
test('encrypted adapter round-trips Unicode sessions larger than one native value', async () => {
  const raw = memoryStore();
  const store = chunkedStore(raw);
  const text = 'ಕನ್ನಡ हिन्दी'.repeat(500);
  await store.setItem('session', text);
  expect(await store.getItem('session')).toBe(text);
  await store.removeItem('session');
  expect(await store.getItem('session')).toBeNull();
});
test('failed chunk write preserves previously committed session', async () => {
  const raw = memoryStore();
  const store = chunkedStore(raw);
  await store.setItem('session', 'old');
  const write = raw.setItem;
  raw.setItem = jest.fn(async (key, value) => {
    if (key.endsWith('.1')) throw new Error('full');
    await write(key, value);
  });
  await expect(store.setItem('session', 'x'.repeat(900))).rejects.toThrow(
    'full',
  );
  expect(await store.getItem('session')).toBe('old');
});
test('cache is consented, user-scoped, bounded and expires; future timestamps rejected', async () => {
  const store = memoryStore();
  const journey = {
    savedAt: new Date().toISOString(),
    request,
    response: parsePlan(fixture),
  };
  expect(cacheJourney(emptyLibrary(), journey).journeys).toEqual([]);
  const library = cacheJourney(
    { ...emptyLibrary(), cacheEnabled: true },
    journey,
  );
  await store.setItem(libraryKey('one'), JSON.stringify(library));
  expect((await loadLibrary(store, 'one')).journeys).toHaveLength(1);
  expect((await loadLibrary(store, 'two')).journeys).toHaveLength(0);
  expect(cacheValid(new Date(Date.now() - 86400001).toISOString())).toBe(false);
  expect(cacheValid(new Date(Date.now() + 60000).toISOString())).toBe(false);
});
test('corrupt saved data is discarded without breaking startup', async () => {
  const store = memoryStore();
  await store.setItem(libraryKey('one'), '{bad');
  expect(await loadLibrary(store, 'one')).toEqual(emptyLibrary());
});
test('search and nearby use only authored stops, not real transport inference', () => {
  expect(searchPlaces('metro').map((p) => p.id)).toEqual(['C', 'D']);
  expect(nearbyPlaces(0, 0)).toEqual([]);
  expect(
    nearbyPlaces(fixtureStops[0]!.latitude, fixtureStops[0]!.longitude)[0]?.id,
  ).toBe('A');
});
test('Kannada/Hindi keys and explicit English fallback are available', () => {
  expect(translator('kn')('home')).toBe('ಯೋಜನೆ');
  expect(translator('hi')('home')).toBe('योजना');
  expect(translator('kn')('cacheNotice')).toBe(translator('en')('cacheNotice'));
});
