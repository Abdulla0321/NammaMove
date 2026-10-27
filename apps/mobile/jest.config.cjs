module.exports = {
    preset: 'jest-expo',
    testMatch: ['**/__tests__/**/*.test.[jt]s?(x)'],
    setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
    collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/generated/**'],
};
