import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: 'NammaMove',
  slug: 'nammamove',
  version: '0.4.0',
  scheme: 'nammamove',
  orientation: 'default',
  userInterfaceStyle: 'light',
  backgroundColor: '#F4F7F5',
  android: {
    package: 'work.nammamove.commuter',
    config: {
      googleMaps: { apiKey: process.env.EXPO_PUBLIC_GOOGLE_MAPS_KEY ?? '' },
    },
    blockedPermissions: ['android.permission.ACCESS_BACKGROUND_LOCATION'],
  },
  ios: { bundleIdentifier: 'work.nammamove.commuter', supportsTablet: true },
  plugins: [
    'expo-secure-store',
    [
      'expo-location',
      { locationWhenInUsePermission: 'Find nearby stops only when you ask.' },
    ],
    '@react-native-community/datetimepicker',
  ],
  web: { name: 'NammaMove', shortName: 'NammaMove', bundler: 'metro' },
};
export default config;
