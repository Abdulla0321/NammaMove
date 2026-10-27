import React from 'react';
import { StopDiagram, type MapProps } from './StopDiagram';
export default function MapFallback({ itinerary }: MapProps) {
  return <StopDiagram itinerary={itinerary} />;
}
