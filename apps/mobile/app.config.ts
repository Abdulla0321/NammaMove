import type { ExpoConfig } from 'expo/config';

const androidMapsKey = process.env.EXPO_PUBLIC_GOOGLE_MAPS_KEY?.trim();
// EAS reads metadata before loading cloud variables; validate only on Android workers.
if (
  process.env.EAS_BUILD === 'true' &&
  process.env.EAS_BUILD_PLATFORM === 'android' &&
  process.env.NAMMAMOVE_REQUIRE_ANDROID_MAPS === 'true' &&
  !androidMapsKey
) {
  throw new Error(
    'Custom Android map build requires an owner-authorized Maps key in the build environment.',
  );
}

const config: ExpoConfig = {
  name: 'NammaMove',
  slug: 'nammamove',
  owner: 'abood21s-team',
  extra: {
    eas: { projectId: '4b408848-1521-455e-93ec-c04605b59204' },
  },
  version: '0.4.0',
  scheme: 'nammamove',
  orientation: 'default',
  userInterfaceStyle: 'light',
  backgroundColor: '#F4F7F5',
  android: {
    package: 'work.nammamove.commuter',
    blockedPermissions: ['android.permission.ACCESS_BACKGROUND_LOCATION'],
  },
  ios: { bundleIdentifier: 'work.nammamove.commuter', supportsTablet: true },
  plugins: [
    'expo-secure-store',
    [
      'react-native-maps',
      androidMapsKey ? { androidGoogleMapsApiKey: androidMapsKey } : {},
    ],
    [
      'expo-location',
      { locationWhenInUsePermission: 'Find nearby stops only when you ask.' },
    ],
    '@react-native-community/datetimepicker',
  ],
  web: { name: 'NammaMove', shortName: 'NammaMove', bundler: 'metro' },
};
export default config;
