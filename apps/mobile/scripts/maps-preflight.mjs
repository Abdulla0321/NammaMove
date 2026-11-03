// Local configuration check only: never prints resolved config/key or starts a build.
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const workspace = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const cli = resolve(dirname(require.resolve('expo/package.json')), 'bin/cli');
try {
    const output = execFileSync(
        process.execPath,
        [cli, 'config', '--type', 'prebuild', '--json'],
        {
            cwd: workspace,
            encoding: 'utf8',
            stdio: ['ignore', 'pipe', 'pipe'],
            maxBuffer: 4 * 1024 * 1024,
        },
    );
    const config = JSON.parse(output);
    if (config.android?.package !== 'work.nammamove.commuter') {
        console.error(
            'Blocked: Android package must remain work.nammamove.commuter.',
        );
        process.exit(1);
    }
    const plugin = config.plugins?.find(
        (item) => Array.isArray(item) && item[0] === 'react-native-maps',
    );
    if (!plugin?.[1]?.androidGoogleMapsApiKey?.trim()) {
        console.error(
            'Blocked: owner-authorized Android Maps key is not configured. Add it privately to the mobile environment.',
        );
        process.exit(1);
    }
    console.log(
        'Local Maps plugin/key presence and Android package check passed.',
    );
    console.log(
        'Google API enablement, billing status, key authorization and signing SHA-1 still require owner verification. No build started.',
    );
} catch {
    // The CLI may include private configuration in its output/errors; do not relay it.
    console.error(
        'Blocked: Expo configuration could not be validated. Verify the private mobile/build environment; no raw configuration was printed.',
    );
    process.exit(1);
}
