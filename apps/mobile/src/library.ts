import { z } from 'zod';
import type { Library, CachedJourney } from './types';
import { emptyLibrary } from './types';
import { responseSchema } from './validation';
import type { KeyStore } from './storage';

const point = z.object({
  stop_id: z.string().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
});
const place = z.object({
  id: z.string(),
  name: z.string(),
  point,
  latitude: z.number(),
  longitude: z.number(),
  label: z.literal('simulation'),
});
const request = z
  .object({ origin: point, destination: point, when: z.string() })
  .passthrough();
const schema = z.object({
  favorites: z.array(place).max(10),
  recent: z
    .array(z.object({ origin: place, destination: place, when: z.string() }))
    .max(5),
  journeys: z
    .array(z.object({ savedAt: z.string(), request, response: responseSchema }))
    .max(3),
  cacheEnabled: z.boolean(),
});
export const libraryKey = (userId: string) => `nammamove.library.${userId}`;
export async function loadLibrary(
  store: KeyStore,
  userId: string,
): Promise<Library> {
  const key = libraryKey(userId);
  try {
    const raw = await store.getItem(key);
    if (!raw) return emptyLibrary();
    const result = schema.parse(JSON.parse(raw));
    // Requests are retained for display only and never automatically executed.
    const journeys = result.cacheEnabled
      ? result.journeys.filter((item) => cacheValid(item.savedAt))
      : [];
    return { ...result, journeys } as Library;
  } catch {
    await store.removeItem(key);
    return emptyLibrary();
  }
}
export function cacheValid(savedAt: string, now = Date.now()): boolean {
  const age = now - Date.parse(savedAt);
  return Number.isFinite(age) && age >= 0 && age < 86400000;
}
export function cacheJourney(
  library: Library,
  journey: CachedJourney,
): Library {
  if (!library.cacheEnabled) return library;
  const compact = {
    ...journey,
    response: {
      ...journey.response,
      itineraries: journey.response.itineraries.slice(0, 2),
    },
  };
  return {
    ...library,
    journeys: [
      compact,
      ...library.journeys.filter(
        (j) =>
          cacheValid(j.savedAt) &&
          JSON.stringify(j.request) !== JSON.stringify(journey.request),
      ),
    ].slice(0, 3),
  };
}
