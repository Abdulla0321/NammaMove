import React, { useState } from 'react';
import { Platform, View } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Button, Field, styles } from './ui';

export default function TimePicker({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange(value: string): void;
  label: string;
}) {
  const [mode, setMode] = useState<'date' | 'time' | null>(null);
  const parsed = new Date(value);
  return (
    <View style={{ gap: 8 }}>
      <Field
        label={label}
        value={value}
        onChangeText={onChange}
        autoCapitalize="none"
        placeholder="2026-10-26T07:55:00+05:30"
      />
      {Platform.OS !== 'web' && (
        <View style={styles.row}>
          <Button
            title="Choose date"
            secondary
            onPress={() => setMode('date')}
          />
          <Button
            title="Choose time"
            secondary
            onPress={() => setMode('time')}
          />
        </View>
      )}
      {mode && Platform.OS !== 'web' && (
        <DateTimePicker
          mode={mode}
          value={Number.isFinite(parsed.getTime()) ? parsed : new Date()}
          onChange={(_event, date) => {
            setMode(null);
            if (date) onChange(date.toISOString());
          }}
        />
      )}
    </View>
  );
}
