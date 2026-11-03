import { AppState, Platform } from 'react-native';
import { isRunningInExpoGo } from 'expo';
import { createServices } from '../src/services';
import * as Location from 'expo-location';

jest.mock('expo', () => ({
  ...jest.requireActual('expo'),
  isRunningInExpoGo: jest.fn(),
}));
jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
}));
jest.mock('@supabase/supabase-js', () => ({
  createClient: jest.fn(() => ({ auth: {} })),
}));

const original = { ...process.env };
afterEach(() => {
  process.env = { ...original };
  jest.restoreAllMocks();
});

test.each([
  [true, undefined, true],
  [false, undefined, false],
] as const)(
  'actual service wiring: Expo Go=%s key=%s offers basemap=%s',
  (expoGo, key, expected) => {
    jest.replaceProperty(Platform, 'OS', 'android');
    jest
      .spyOn(AppState, 'addEventListener')
      .mockReturnValue({ remove: jest.fn() });
    jest.mocked(isRunningInExpoGo).mockReturnValue(expoGo);
    process.env.EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8000';
    process.env.EXPO_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321';
    process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_test';
    if (key === undefined) delete process.env.EXPO_PUBLIC_GOOGLE_MAPS_KEY;
    else process.env.EXPO_PUBLIC_GOOGLE_MAPS_KEY = key;
    const services = createServices();
    expect(services.mapEnabled).toBe(expected);
    // Viewing fixed route endpoints must never request location permission.
    expect(Location.requestForegroundPermissionsAsync).not.toHaveBeenCalled();
  },
);
