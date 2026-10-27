import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import openapiTS, { astToString } from 'openapi-typescript';

const root = resolve('../..');
const python =
    process.env.PYTHON ??
    resolve(
        root,
        process.platform === 'win32'
            ? '.venv/Scripts/python.exe'
            : '.venv/bin/python',
    );
const code = `import sys,json
sys.path.insert(0,'backend')
from app.main import create_app
from app.config import Settings
s=create_app(Settings(_env_file=None)).openapi()
s['paths']={k:v for k,v in s['paths'].items() if k=='/v1/routing/plan'}
names=['Point','PlanRequest','PlanResponse','Itinerary','Leg','HTTPValidationError','ValidationError']
s['components']['schemas']={k:v for k,v in s['components']['schemas'].items() if k in names}
print(json.dumps(s))`;
const schema = JSON.parse(
    execFileSync(python, ['-c', code], { cwd: root, encoding: 'utf8' }),
);
const output = astToString(await openapiTS(schema));
const target = resolve('src/generated/api.ts');
if (process.argv.includes('--check')) {
    if (readFileSync(target, 'utf8') !== output)
        throw new Error('Routing contracts drifted; regenerate and review.');
    console.log('Routing OpenAPI contracts match backend.');
} else {
    writeFileSync(target, output);
    console.log('Generated routing contracts from FastAPI OpenAPI.');
}
