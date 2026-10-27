import 'react-native-url-polyfill/auto';
import { AppState, Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as Location from 'expo-location';
import { createClient } from '@supabase/supabase-js';
import { chunkedStore, memoryStore, type KeyStore } from './storage';
import { apiClient } from './api';
import type { PlanRequest, PlanResponse, Session } from './types';

export interface Services {
  store: KeyStore;
  auth: {
    session(): Promise<Session | null>;
    subscribe(callback: (session: Session | null) => void): () => void;
    signIn(email: string, password: string): Promise<void>;
    signUp(email: string, password: string): Promise<boolean>;
    signOut(): Promise<void>;
  };
  plan(request: PlanRequest): Promise<PlanResponse>;
  health(): Promise<boolean>;
  locate(): Promise<{ latitude: number; longitude: number }>;
  mapEnabled: boolean;
}

export function configuration() {
  const api = process.env.EXPO_PUBLIC_API_URL ?? '';
  const supabase = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
  const key = process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? '';
  for (const value of [api, supabase]) {
    const url = new URL(value);
    const local =
      __DEV__ && ['localhost', '127.0.0.1', '10.0.2.2'].includes(url.hostname);
    if (
      (!local && url.protocol !== 'https:') ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      url.pathname !== '/'
    )
      throw new Error(
        'Use HTTPS origins (emulator HTTP allowed in development).',
      );
  }
  if (!key || key.startsWith('sb_secret_'))
    throw new Error('Configure a public Supabase publishable/anon key.');
  if (!key.startsWith('sb_publishable_') && !key.startsWith('eyJ'))
    throw new Error('Use a public publishable or anon key.');
  if (key.startsWith('eyJ')) {
    // Never accept a legacy service_role key in a distributable client.
    const claims = JSON.parse(
      atob(key.split('.')[1]!.replace(/-/g, '+').replace(/_/g, '/')),
    ) as { role?: string };
    if (claims.role !== 'anon')
      throw new Error('Only a public anon key is allowed.');
  }
  return { api: api.replace(/\/$/, ''), supabase, key };
}

export function createServices(): Services {
  const config = configuration();
  const store =
    Platform.OS === 'web'
      ? memoryStore()
      : chunkedStore({
          getItem: (key) => SecureStore.getItemAsync(key),
          setItem: (key, value) =>
            SecureStore.setItemAsync(key, value, {
              keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
            }),
          removeItem: (key) => SecureStore.deleteItemAsync(key),
        });
  const client = createClient(config.supabase, config.key, {
    auth: {
      storage: store,
      persistSession: Platform.OS !== 'web',
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  });
  if (Platform.OS !== 'web')
    AppState.addEventListener('change', (state) => {
      if (state === 'active') client.auth.startAutoRefresh();
      else client.auth.stopAutoRefresh();
    });
  const api = apiClient(config.api, {
    token: async () =>
      (await client.auth.getSession()).data.session?.access_token ?? null,
    refresh: async () =>
      (await client.auth.refreshSession()).data.session?.access_token ?? null,
  });
  return {
    store,
    ...api,
    auth: {
      session: async () => {
        const { data } = await client.auth.getSession();
        return data.session ? { userId: data.session.user.id } : null;
      },
      subscribe: (callback) => {
        const { data } = client.auth.onAuthStateChange((_event, session) =>
          callback(session ? { userId: session.user.id } : null),
        );
        return () => data.subscription.unsubscribe();
      },
      signIn: async (email, password) => {
        const { error } = await client.auth.signInWithPassword({
          email,
          password,
        });
        if (error)
          throw new Error(
            'Sign-in failed. Check your credentials and connection.',
          );
      },
      signUp: async (email, password) => {
        const { data, error } = await client.auth.signUp({ email, password });
        if (error)
          throw new Error(
            'Account creation unavailable. Check the form and connection.',
          );
        return !!data.session;
      },
      signOut: async () => {
        const { error } = await client.auth.signOut({ scope: 'local' });
        if (error) throw new Error('Could not clear this session. Retry.');
      },
    },
    locate: async () => {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (!permission.granted) throw new Error('denied');
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };
    },
    mapEnabled: !!process.env.EXPO_PUBLIC_GOOGLE_MAPS_KEY,
  };
}
