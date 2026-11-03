import React from 'react';
import { Text, View } from 'react-native';
import type { Itinerary } from './types';
import { colors, styles } from './ui';
import { translator, type Translate } from './i18n';

export interface MapProps {
  itinerary: Itinerary;
  enabled: boolean;
  t?: Translate;
}
export function StopDiagram({
  itinerary,
  t = translator('en'),
}: Pick<MapProps, 'itinerary' | 't'>) {
  const points = itinerary.legs.flatMap((leg, index) => [
    ...(index === 0
      ? [{ latitude: leg.from_lat, longitude: leg.from_lon }]
      : []),
    { latitude: leg.to_lat, longitude: leg.to_lon },
  ]);
  const lats = points.map((p) => p.latitude),
    lons = points.map((p) => p.longitude);
  const minLat = Math.min(...lats),
    minLon = Math.min(...lons);
  const latRange = Math.max(0.001, Math.max(...lats) - minLat);
  const lonRange = Math.max(0.001, Math.max(...lons) - minLon);
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{t('mapOverview')}</Text>
      <Text style={styles.muted}>{t('mapApproximate')}</Text>
      <View
        accessible
        accessibilityLabel={t('mapEndpoints')}
        style={{
          height: 170,
          backgroundColor: '#E9F1EC',
          borderRadius: 14,
          margin: 8,
        }}
      >
        {points.map((p, i) => (
          <View
            key={i}
            style={{
              position: 'absolute',
              left: `${8 + ((p.longitude - minLon) / lonRange) * 76}%`,
              top: `${80 - ((p.latitude - minLat) / latRange) * 65}%`,
              width: 28,
              height: 28,
              borderRadius: 14,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: colors.green,
            }}
          >
            <Text style={{ color: colors.white, fontWeight: '700' }}>
              {i + 1}
            </Text>
          </View>
        ))}
      </View>
      {points.map((p, i) => (
        <Text key={i} style={styles.muted}>
          {i + 1}. {p.latitude.toFixed(4)}, {p.longitude.toFixed(4)}
        </Text>
      ))}
    </View>
  );
}
