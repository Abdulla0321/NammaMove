import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

const workspace = resolve(__dirname, '..');
const configModule = createRequire(resolve(workspace, 'package.json')).resolve(
  '@expo/config',
);
const program = `
const { getConfig } = require(${JSON.stringify(configModule)});
try {
  const c = getConfig(process.cwd()).exp;
  console.log(JSON.stringify({projectId:c.extra?.eas?.projectId, owner:c.owner,
    androidPackage:c.android?.package,
    mapsPlugin:c.plugins?.some(p=>Array.isArray(p)&&p[0]==='react-native-maps')}));
} catch (error) {
  process.stderr.write(error.message.includes('Custom Android map build requires') ? 'MAPS_KEY_REQUIRED' : 'UNEXPECTED_CONFIG_ERROR');
  process.exitCode = 1;
}`;

function evaluate(build?: string, platform?: string) {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    EXPO_NO_DOTENV: '1',
    NAMMAMOVE_REQUIRE_ANDROID_MAPS: 'true',
  };
  delete env.EXPO_PUBLIC_GOOGLE_MAPS_KEY;
  delete env.EAS_BUILD;
  delete env.EAS_BUILD_PLATFORM;
  if (build) env.EAS_BUILD = build;
  if (platform) env.EAS_BUILD_PLATFORM = platform;
  return spawnSync(process.execPath, ['-e', program], {
    cwd: workspace,
    env,
    encoding: 'utf8',
  });
}

test('EAS metadata evaluation works before cloud Maps credentials are loaded', () => {
  const result = evaluate();
  expect(result.status).toBe(0);
  expect(JSON.parse(result.stdout)).toEqual({
    projectId: '4b408848-1521-455e-93ec-c04605b59204',
    owner: 'abood21s-team',
    androidPackage: 'work.nammamove.commuter',
    mapsPlugin: true,
  });
});
test('an actual Android worker configuration still rejects a missing Maps key', () => {
  const result = evaluate('true', 'android');
  expect(result.status).toBe(1);
  expect(result.stderr).toBe('MAPS_KEY_REQUIRED');
});
test('the Android Maps key guard does not block an iOS configuration', () => {
  expect(evaluate('true', 'ios').status).toBe(0);
});
