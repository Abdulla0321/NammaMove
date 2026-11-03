import React, { useState } from 'react';
import { View, Text } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import type { MapProps } from './StopDiagram';
import { StopDiagram } from './StopDiagram';
import { Button, styles } from './ui';
import { translator } from './i18n';

export default function RouteMap({
  itinerary,
  enabled,
  t = translator('en'),
}: MapProps) {
  const [open, setOpen] = useState(false);
  const first = itinerary.legs[0];
  return (
    <View style={{ gap: 12 }}>
      <StopDiagram itinerary={itinerary} t={t} />
      {!enabled && <Text style={styles.muted}>{t('mapUnavailable')}</Text>}
      {enabled && first && (
        <>
          <Text style={styles.muted}>{t('mapPrivacy')}</Text>
          <Button
            title={open ? t('hideMap') : t('showMap')}
            secondary
            onPress={() => setOpen(!open)}
          />
          {open && (
            <MapView
              accessibilityLabel={t('mapLabel')}
              style={{ width: '100%', height: 280, borderRadius: 20 }}
              initialRegion={{
                latitude: first.from_lat,
                longitude: first.from_lon + 0.012,
                latitudeDelta: 0.025,
                longitudeDelta: 0.045,
              }}
              showsUserLocation={false}
            >
              {itinerary.legs.map((leg, i) => (
                <React.Fragment key={i}>
                  <Marker
                    coordinate={{
                      latitude: leg.from_lat,
                      longitude: leg.from_lon,
                    }}
                    title={t('mapStep', {
                      number: i + 1,
                      mode: t(
                        leg.mode === 'BUS'
                          ? 'bus'
                          : leg.mode === 'WALK'
                            ? 'walk'
                            : 'metro',
                      ),
                    })}
                  />
                  <Polyline
                    coordinates={[
                      { latitude: leg.from_lat, longitude: leg.from_lon },
                      { latitude: leg.to_lat, longitude: leg.to_lon },
                    ]}
                    strokeColor={leg.mode === 'WALK' ? '#725000' : '#146349'}
                    strokeWidth={4}
                    lineDashPattern={leg.mode === 'WALK' ? [5, 5] : undefined}
                  />
                </React.Fragment>
              ))}
              <Marker
                coordinate={{
                  latitude: itinerary.legs[itinerary.legs.length - 1]!.to_lat,
                  longitude: itinerary.legs[itinerary.legs.length - 1]!.to_lon,
                }}
                title={t('mapDestination')}
              />
            </MapView>
          )}
        </>
      )}
    </View>
  );
}
