import { defineConfig } from 'eslint/config';
import expo from 'eslint-config-expo/flat.js';

export default defineConfig([
    expo,
    { ignores: ['dist/**', 'coverage/**', 'src/generated/**'] },
    {
        files: ['**/*.ts', '**/*.tsx'],
        rules: { '@typescript-eslint/no-explicit-any': 'error' },
    },
]);
