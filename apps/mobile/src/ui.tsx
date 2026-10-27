import React from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from 'react-native';

export const colors = {
  ink: '#142D29',
  muted: '#475F59',
  green: '#146349',
  lime: '#DCEC9C',
  paper: '#F4F7F5',
  white: '#FFFFFF',
  line: '#CDDBD3',
  amber: '#725000',
  pale: '#FFF2CC',
  red: '#9C2935',
};
export function Button({
  title,
  onPress,
  secondary = false,
  disabled = false,
}: {
  title: string;
  onPress(): void;
  secondary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary && styles.secondary,
        (pressed || disabled) && { opacity: 0.65 },
      ]}
    >
      <Text style={[styles.buttonText, secondary && { color: colors.green }]}>
        {title}
      </Text>
    </Pressable>
  );
}
export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        style={styles.input}
        {...props}
      />
    </View>
  );
}
export function Chip({
  title,
  selected,
  onPress,
}: {
  title: string;
  selected: boolean;
  onPress(): void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[
        styles.chip,
        selected && {
          backgroundColor: colors.green,
          borderColor: colors.green,
        },
      ]}
    >
      <Text style={[styles.chipText, selected && { color: colors.white }]}>
        {title}
      </Text>
    </Pressable>
  );
}
export function Notice({
  children,
  error = false,
}: {
  children: React.ReactNode;
  error?: boolean;
}) {
  return (
    <View style={[styles.notice, error && { borderColor: colors.red }]}>
      <Text
        accessibilityLiveRegion={error ? 'assertive' : 'polite'}
        style={[styles.body, error && { color: colors.red }]}
      >
        {children}
      </Text>
    </View>
  );
}
export const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.paper },
  header: {
    paddingHorizontal: 22,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  brand: {
    fontSize: 25,
    fontWeight: '800',
    color: colors.green,
    letterSpacing: -1,
  },
  content: {
    padding: 20,
    gap: 18,
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    paddingBottom: 36,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1.5,
    color: colors.green,
  },
  title: {
    fontSize: 32,
    lineHeight: 39,
    fontWeight: '800',
    color: colors.ink,
    letterSpacing: -0.8,
  },
  heading: { fontSize: 22, fontWeight: '700', color: colors.ink },
  body: { fontSize: 16, lineHeight: 24, color: colors.ink },
  muted: { fontSize: 14, lineHeight: 21, color: colors.muted },
  card: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 22,
    padding: 20,
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    alignItems: 'center',
  },
  label: { fontSize: 14, fontWeight: '700', color: colors.ink },
  field: { gap: 7 },
  input: {
    minHeight: 52,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 14,
    color: colors.ink,
    backgroundColor: colors.white,
    fontSize: 16,
  },
  button: {
    minHeight: 50,
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 14,
    backgroundColor: colors.green,
    justifyContent: 'center',
    alignItems: 'center',
  },
  secondary: {
    backgroundColor: '#E9F1EC',
    borderWidth: 1,
    borderColor: colors.line,
  },
  buttonText: {
    fontSize: 16,
    color: colors.white,
    fontWeight: '700',
    textAlign: 'center',
  },
  chip: {
    minHeight: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.line,
    paddingVertical: 12,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  chipText: { fontSize: 14, fontWeight: '600', color: colors.ink },
  notice: {
    padding: 14,
    borderWidth: 1,
    borderColor: '#DDC677',
    borderRadius: 14,
    backgroundColor: colors.pale,
  },
  nav: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    flexWrap: 'wrap',
    padding: 8,
    gap: 6,
    borderTopWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  skeleton: {
    height: 18,
    borderRadius: 9,
    backgroundColor: '#DFE8E2',
    marginVertical: 5,
  },
});
