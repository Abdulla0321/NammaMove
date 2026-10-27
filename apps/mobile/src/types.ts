import type { components } from './generated/api';

export type PlanRequest = components['schemas']['PlanRequest'];
export type PlanResponse = components['schemas']['PlanResponse'];
export type Itinerary = components['schemas']['Itinerary'];
export type Point = components['schemas']['Point'];
export type Preference = PlanRequest['preference'];
export type Place = {
  id: string;
  name: string;
  point: Point;
  latitude: number;
  longitude: number;
  label: 'simulation';
};
export type Session = { userId: string };
export type CachedJourney = {
  savedAt: string;
  request: PlanRequest;
  response: PlanResponse;
};
export type Library = {
  favorites: Place[];
  recent: { origin: Place; destination: Place; when: string }[];
  journeys: CachedJourney[];
  cacheEnabled: boolean;
};
export const emptyLibrary = (): Library => ({
  favorites: [],
  recent: [],
  journeys: [],
  cacheEnabled: false,
});
