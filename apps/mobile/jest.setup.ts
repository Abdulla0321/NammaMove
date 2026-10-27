jest.mock('react-native-maps', () => ({
  __esModule: true,
  default: 'MapView',
  Marker: 'Marker',
  Polyline: 'Polyline',
}));
jest.mock('@react-native-community/datetimepicker', () => 'DateTimePicker');
