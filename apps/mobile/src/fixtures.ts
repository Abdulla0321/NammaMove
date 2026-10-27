import type { Place } from './types';

// Independently authored Phase 03 stops. Never merge these IDs with catalog IDs.
export const fixtureStops: Place[] = [
  {
    id: 'A',
    name: 'Simulation A · Bus departure',
    point: { stop_id: 'A' },
    latitude: 12.97,
    longitude: 77.59,
    label: 'simulation',
  },
  {
    id: 'B',
    name: 'Simulation B · Bus interchange',
    point: { stop_id: 'B' },
    latitude: 12.97,
    longitude: 77.6,
    label: 'simulation',
  },
  {
    id: 'C',
    name: 'Simulation C · Metro interchange',
    point: { stop_id: 'C' },
    latitude: 12.971,
    longitude: 77.6,
    label: 'simulation',
  },
  {
    id: 'D',
    name: 'Simulation D · Metro destination',
    point: { stop_id: 'D' },
    latitude: 12.971,
    longitude: 77.62,
    label: 'simulation',
  },
];
export function searchPlaces(query: string): Place[] {
  return fixtureStops.filter((p) =>
    `${p.id} ${p.name}`.toLowerCase().includes(query.trim().toLowerCase()),
  );
}
export function nearbyPlaces(
  latitude: number,
  longitude: number,
): (Place & { distance: number })[] {
  const rad = Math.PI / 180;
  return fixtureStops
    .map((place) => {
      const a =
        Math.sin(((place.latitude - latitude) * rad) / 2) ** 2 +
        Math.cos(latitude * rad) *
          Math.cos(place.latitude * rad) *
          Math.sin(((place.longitude - longitude) * rad) / 2) ** 2;
      return {
        ...place,
        distance: 6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, a))),
      };
    })
    .filter((p) => p.distance <= 1000)
    .sort((a, b) => a.distance - b.distance);
}
