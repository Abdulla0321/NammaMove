// Explicit opt-in real services only. Never print credentials, tokens or bodies.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { apiClient } from '../src/api';
import type { PlanRequest } from '../src/types';

const file = process.env.NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG;
const base = process.env.NAMMAMOVE_MOBILE_TEST_API_URL;
if (!file || !base)
    throw new Error(
        'Set ignored Auth config and actual local API URL; no mocks or skip substitution.',
    );
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const config = JSON.parse(readFileSync(file, 'utf8')) as {
    supabase_url: string;
    users: { email: string; password: string }[];
};
assert(
    ['localhost', '127.0.0.1'].includes(new URL(config.supabase_url).hostname),
);
let checks = 0;
for (const origin of [
    'http://localhost:8081',
    'http://127.0.0.1:8081',
    'https://untrusted.example',
]) {
    const preflight = await fetch(
        `${config.supabase_url}/auth/v1/token?grant_type=password`,
        {
            method: 'OPTIONS',
            headers: {
                Origin: origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers':
                    'apikey,authorization,content-type,x-client-info,x-supabase-api-version',
            },
        },
    );
    assert.equal(preflight.status, 204);
    assert.equal(
        preflight.headers.get('access-control-allow-origin'),
        origin.startsWith('http://') ? origin : null,
    );
    checks++;
}
const user = config.users[0]!;
const login = await fetch(
    `${config.supabase_url}/auth/v1/token?grant_type=password`,
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Origin: 'http://localhost:8081',
            apikey: 'sb_publishable_local-development',
            Authorization: 'Bearer sb_publishable_local-development',
            'X-Client-Info': 'supabase-js-web-test',
            'X-Supabase-Api-Version': '2024-01-01',
        },
        body: JSON.stringify(user),
    },
);
assert.equal(login.status, 200);
assert.equal(
    login.headers.get('access-control-allow-origin'),
    'http://localhost:8081',
);
const session = (await login.json()) as { access_token: string };
const client = apiClient(base, {
    token: async () => session.access_token,
    refresh: async () => null,
});
const request: PlanRequest = {
    origin: { stop_id: 'A' },
    destination: { stop_id: 'D' },
    when: '2026-10-26T07:55:00+05:30',
    wheelchair: true,
    transit_required: true,
    max_walk_m: 500,
    modes: ['BUS', 'SUBWAY', 'WALK'],
    preference: 'fastest',
    arrive_by: false,
    max_transfers: 3,
    limit: 5,
};
assert(await client.health());
checks++;
for (const pref of [
    'fastest',
    'cheapest',
    'fewest_transfers',
    'least_walking',
] as const) {
    const result = await client.plan({ ...request, preference: pref });
    assert.equal(result.status, 'ok');
    assert.equal(result.data_mode, 'simulation');
    assert.equal(
        result.itineraries[0]!.fare_inr,
        ['fastest', 'cheapest'].includes(pref) ? 30 : 50,
    );
    checks++;
}
const bus = await client.plan({
    ...request,
    destination: { stop_id: 'B' },
    modes: ['BUS', 'WALK'],
});
assert.equal(bus.itineraries[0]!.fare_inr, 20);
checks++;
assert.equal(
    (await client.plan({ ...request, when: '2026-10-26T08:40:00+05:30' }))
        .status,
    'no_route',
);
checks++;
const bad = apiClient(base, {
    token: async () => 'invalid',
    refresh: async () => null,
});
await assert.rejects(bad.plan(request), { code: 'unauthorized' });
checks++;
console.log(
    `${checks} real mobile-client/API checks passed (genuine Supabase and OTP; synthetic data only).`,
);
