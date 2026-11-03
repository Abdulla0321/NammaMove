import { dictionaries, en, translator, type Key } from '../src/i18n';

test.each(['kn', 'hi'] as const)(
  '%s has every UI string and matching placeholders',
  (language) => {
    const keys = Object.keys(en) as Key[];
    expect(Object.keys(dictionaries[language]).sort()).toEqual(keys.sort());
    for (const key of keys) {
      expect(dictionaries[language][key].trim()).not.toBe('');
      expect(dictionaries[language][key]).toMatch(
        language === 'kn' ? /[\u0C80-\u0CFF]/ : /[\u0900-\u097F]/,
      );
      expect(dictionaries[language][key]).not.toContain('???');
      expect(dictionaries[language][key].match(/\{\w+\}/g) ?? []).toEqual(
        en[key].match(/\{\w+\}/g) ?? [],
      );
    }
  },
);
test('missing and blank translations fall back to English with interpolation', () => {
  expect(translator('kn', {})('cacheNotice')).toBe(en.cacheNotice);
  expect(translator('hi', { remove: ' ' })('remove', { place: 'A' })).toBe(
    'Remove A',
  );
  expect(translator('kn')('walkInstruction', { distance: 25 })).toContain('25');
});
