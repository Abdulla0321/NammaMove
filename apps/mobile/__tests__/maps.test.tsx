import React from 'react';
import { fireEventAsync, render, screen } from '@testing-library/react-native';
import RouteMap from '../src/RouteMap.native';
import { canShowBasemap } from '../src/mapRuntime';
import { parsePlan } from '../src/validation';
import { translator } from '../src/i18n';
import fixture from './fixtures/plan.json';

const itinerary = parsePlan(fixture).itineraries[0]!;
const t = translator('en');

test('Expo Go without a project key can open and hide the basemap after consent', async () => {
  await render(
    <RouteMap
      itinerary={itinerary}
      enabled={canShowBasemap('android', true)}
    />,
  );
  expect(screen.getByText(t('mapApproximate'))).toBeTruthy();
  expect(screen.queryByLabelText(t('mapLabel'))).toBeNull();
  await fireEventAsync.press(
    screen.getByRole('button', { name: t('showMap') }),
  );
  const map = screen.getByLabelText(t('mapLabel'));
  expect(map.props.style).toEqual(
    expect.objectContaining({ width: '100%', height: 280 }),
  );
  expect(map.props.showsUserLocation).toBe(false);
  expect(map.props.initialRegion).toEqual(
    expect.objectContaining({
      latitude: 12.97,
      longitude: expect.closeTo(77.602, 4),
    }),
  );
  await fireEventAsync.press(
    screen.getByRole('button', { name: t('hideMap') }),
  );
  expect(screen.queryByLabelText(t('mapLabel'))).toBeNull();
});

test.each([undefined, '', '   '])(
  'custom native binary without a usable key retains an explained endpoint fallback (%s)',
  async (key) => {
    await render(
      <RouteMap
        itinerary={itinerary}
        enabled={canShowBasemap('android', false, key)}
      />,
    );
    expect(screen.getByText(t('mapUnavailable'))).toBeTruthy();
    expect(screen.getByText(t('mapApproximate'))).toBeTruthy();
    expect(screen.queryByRole('button', { name: t('showMap') })).toBeNull();
    expect(screen.queryByLabelText(t('mapLabel'))).toBeNull();
  },
);

test('a configured custom binary offers opt-in maps; web remains endpoint-only', async () => {
  await render(
    <RouteMap
      itinerary={itinerary}
      enabled={canShowBasemap('android', false, 'test-public-key')}
    />,
  );
  expect(screen.getByRole('button', { name: t('showMap') })).toBeTruthy();
  expect(canShowBasemap('web', true, 'test-public-key')).toBe(false);
});
