import React from 'react';
import * as Native from 'react-native';
import {
  act,
  fireEventAsync as fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react-native';
import { CommuterApp } from '../App';
import { ClientError } from '../src/api';
import { memoryStore } from '../src/storage';
import { parsePlan } from '../src/validation';
import { emptyLibrary } from '../src/types';
import { libraryKey } from '../src/library';
import type { Services } from '../src/services';
import fixture from './fixtures/plan.json';

jest.mock('../src/services', () => ({ createServices: jest.fn() }));
jest.mock(
  'react-native-safe-area-context',
  () => jest.requireActual('react-native-safe-area-context/jest/mock').default,
);

async function setup(overrides: Partial<Services> = {}) {
  const store = memoryStore();
  await store.setItem('nammamove.onboarded', 'yes');
  const services: Services = {
    store,
    mapEnabled: false,
    auth: {
      session: async () => ({ userId: 'one' }),
      subscribe: () => () => undefined,
      signIn: async () => undefined,
      signUp: async () => false,
      signOut: async () => undefined,
    },
    plan: jest.fn().mockResolvedValue(parsePlan(fixture)),
    health: async () => true,
    locate: jest.fn().mockRejectedValue(new Error('denied')),
    ...overrides,
  };
  await render(<CommuterApp services={services} />);
  await screen.findByRole('button', { name: 'Find journeys' });
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Find journeys' }).props
        .accessibilityState.disabled,
    ).toBe(false),
  );
  return services;
}

afterEach(() => jest.restoreAllMocks());

test.each([320, 800])(
  'planning controls remain accessible at width %s with large text',
  async (width) => {
    jest
      .spyOn(Native, 'useWindowDimensions')
      .mockReturnValue({ width, height: 640, scale: 1, fontScale: 2 });
    await setup();
    expect(screen.getByLabelText('Maximum walking (metres)')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Find journeys' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Settings' })).toBeTruthy();
  },
);

test('onboarding leads to authentication and signup confirmation is explained', async () => {
  const store = memoryStore();
  const services: Services = {
    store,
    mapEnabled: false,
    auth: {
      session: async () => null,
      subscribe: () => () => undefined,
      signIn: jest.fn(),
      signUp: jest.fn().mockResolvedValue(false),
      signOut: jest.fn(),
    },
    plan: jest.fn(),
    health: async () => true,
    locate: jest.fn(),
  };
  await render(<CommuterApp services={services} />);
  await fireEvent.press(
    await screen.findByRole('button', { name: 'Get started' }),
  );
  await fireEvent.changeText(
    screen.getByLabelText('Email'),
    'commuter@example.org',
  );
  await fireEvent.changeText(
    screen.getByLabelText('Password'),
    'not-a-real-secret',
  );
  await fireEvent.press(screen.getByRole('button', { name: 'Create account' }));
  expect(
    await screen.findByText(
      'Check your email to confirm your account, then sign in.',
    ),
  ).toBeTruthy();
  expect(services.auth.signUp).toHaveBeenCalledWith(
    'commuter@example.org',
    'not-a-real-secret',
  );
  expect(screen.queryByRole('button', { name: 'Find journeys' })).toBeNull();
});

test('cached data is cleared before local sign-out', async () => {
  const services = await setup();
  await services.store.setItem(
    libraryKey('one'),
    JSON.stringify(emptyLibrary()),
  );
  const signOut = jest.spyOn(services.auth, 'signOut');
  await fireEvent.press(screen.getByRole('button', { name: 'Settings' }));
  await fireEvent.press(
    screen.getByRole('button', { name: 'Sign out & clear device data' }),
  );
  await screen.findByLabelText('Email');
  expect(signOut).toHaveBeenCalled();
  expect(await services.store.getItem(libraryKey('one'))).toBeNull();
});

test('background token refresh preserves the selected journey', async () => {
  let notify!: Parameters<Services['auth']['subscribe']>[0];
  const auth: Services['auth'] = {
    session: async () => ({ userId: 'one' }),
    subscribe: (callback) => {
      notify = callback;
      return () => undefined;
    },
    signIn: jest.fn(),
    signUp: jest.fn(),
    signOut: jest.fn(),
  };
  await setup({ auth });
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  await screen.findByText('Your journey options');
  await act(async () => notify({ userId: 'one' }));
  expect(screen.getByText('Your journey options')).toBeTruthy();
});

test('home has accessible place selection and journey request; detail gives explicit legs', async () => {
  const services = await setup();
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  await screen.findByText('Your journey options');
  expect(services.plan).toHaveBeenCalledWith(
    expect.objectContaining({
      wheelchair: true,
      preference: 'fastest',
      transit_required: true,
    }),
  );
  expect(screen.getAllByText(/30.*synthetic fare/).length).toBeGreaterThan(0);
  await fireEvent.press(
    screen.getByRole('button', { name: 'Journey details 1' }),
  );
  expect(await screen.findByText('1. Bus')).toBeTruthy();
  expect(screen.getByText('2. Walk')).toBeTruthy();
  expect(screen.getByText('3. Metro')).toBeTruthy();
  expect(
    screen.getByText('Approximate endpoints only; not a street or track path.'),
  ).toBeTruthy();
});
test('destination search updates request instead of inventing a stop', async () => {
  const services = await setup();
  await fireEvent.press(
    screen.getByRole('button', { name: 'Simulation D · Metro destination' }),
  );
  await fireEvent.changeText(
    screen.getByLabelText('Where are you going?'),
    'Bus interchange',
  );
  await fireEvent.press(
    screen.getByRole('button', { name: 'Simulation B · Bus interchange' }),
  );
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  await waitFor(() =>
    expect(services.plan).toHaveBeenCalledWith(
      expect.objectContaining({ destination: { stop_id: 'B' } }),
    ),
  );
});
test('permission denial keeps manual origin and planning available', async () => {
  await setup();
  await fireEvent.press(
    screen.getByRole('button', { name: 'Find nearby stops' }),
  );
  expect(
    await screen.findByText(
      'Location unavailable or permission denied. Choose your starting point manually.',
    ),
  ).toBeTruthy();
  expect(
    screen.getByRole('button', { name: 'Simulation A · Bus departure' }),
  ).toBeTruthy();
});
test('nearby location-derived distances are not retained in recent searches', async () => {
  const services = await setup({
    locate: jest
      .fn()
      .mockResolvedValue({ latitude: 12.97001, longitude: 77.59001 }),
  });
  await fireEvent.press(
    screen.getByRole('button', { name: 'Find nearby stops' }),
  );
  await fireEvent.press(
    await screen.findByRole('button', { name: /Simulation A.*straight-line/ }),
  );
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  await screen.findByText('Your journey options');
  const stored = JSON.parse(
    (await services.store.getItem(libraryKey('one')))!,
  ) as {
    recent: { origin: Record<string, unknown> }[];
  };
  expect(stored.recent[0]?.origin).not.toHaveProperty('distance');
  expect(stored.recent[0]?.origin.latitude).toBe(12.97);
});

test('no-route is an empty state with no detail button', async () => {
  await setup({
    plan: jest.fn().mockResolvedValue(
      parsePlan({
        ...fixture,
        status: 'no_route',
        reason: 'no_feasible_route_in_search_window',
        itineraries: [],
      }),
    ),
  });
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  expect(
    await screen.findByText(
      'No feasible journey for these choices. Try another time, mode or walking limit.',
    ),
  ).toBeTruthy();
  expect(
    screen.queryByRole('button', { name: 'Journey details 1' }),
  ).toBeNull();
});
test('unavailable backend shows meaningful error and saved navigation', async () => {
  await setup({
    plan: jest.fn().mockRejectedValue(new ClientError('offline')),
  });
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  expect(
    await screen.findByText(
      'Offline or backend unavailable. Retry, or open a previously saved journey.',
    ),
  ).toBeTruthy();
  await fireEvent.press(screen.getByRole('button', { name: 'Saved' }));
  expect(
    await screen.findByText(
      'Nothing saved yet. Your places and recent searches stay on this device.',
    ),
  ).toBeTruthy();
});
test('expired invalid session returns to sign-in without exposing old journey', async () => {
  await setup({
    plan: jest.fn().mockRejectedValue(new ClientError('unauthorized')),
  });
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  expect(await screen.findByLabelText('Email')).toBeTruthy();
  expect(screen.queryByText('Your journey options')).toBeNull();
});
test('invalid timezone/time is rejected before calling the backend', async () => {
  const services = await setup();
  await fireEvent.changeText(
    screen.getByLabelText('Date and time with timezone'),
    'bad',
  );
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  expect(
    await screen.findByText(
      'Check the places, time with timezone and walking limit.',
    ),
  ).toBeTruthy();
  expect(services.plan).not.toHaveBeenCalled();
});
test('loading skeleton and disabled planning prevent duplicate requests', async () => {
  let resolve!: (value: ReturnType<typeof parsePlan>) => void;
  await setup({
    plan: jest.fn().mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    ),
  });
  await fireEvent.press(screen.getByRole('button', { name: 'Find journeys' }));
  expect(screen.getByRole('progressbar')).toBeTruthy();
  expect(
    screen.getByRole('button', { name: 'Find journeys' }).props
      .accessibilityState.disabled,
  ).toBe(true);
  await act(async () => resolve(parsePlan(fixture)));
  await screen.findByText('Your journey options');
});
test('cached launch/open is timestamped stale and performs no routing call', async () => {
  const store = memoryStore();
  await store.setItem('nammamove.onboarded', 'yes');
  await store.setItem(
    libraryKey('one'),
    JSON.stringify({
      ...emptyLibrary(),
      cacheEnabled: true,
      journeys: [
        {
          savedAt: new Date().toISOString(),
          request: {
            origin: { stop_id: 'A' },
            destination: { stop_id: 'D' },
            when: '2026-10-26T07:55:00+05:30',
          },
          response: fixture,
        },
      ],
    }),
  );
  const services = await setup({ store });
  await fireEvent.press(screen.getByRole('button', { name: 'Saved' }));
  await fireEvent.press(
    await screen.findByRole('button', { name: 'Open cached journey 1' }),
  );
  expect(
    await screen.findByText('CACHED / STALE · Not a current recommendation', {
      exact: false,
    }),
  ).toBeTruthy();
  expect(services.plan).not.toHaveBeenCalled();
});
