# NammaMove engineering instructions
Work in this existing repository; never initialize a nested repository or rename the project.
Read docs/MASTER_PLAN.md, docs/PHASE_STATUS.md and the relevant phase before implementation.
Preserve API compatibility and existing regression tests. Make focused changes and update phase evidence.

## Safety and truthfulness
- Missing/stale GPS means uncertainty, never confirmed cancellation without independent evidence.
- Separate feed freshness, service status, confidence and incident verification. Only trusted verified evidence may close edges in production; request flags in the simulator are not authorization.
- Rerouting must account for downstream capacity and congestion; the current penalty is illustrative only. Require network impact tests before live automatic rerouting.
- Keep simulation labels visible. No simulated feed may be described as live.
- Never commit credentials, private keys, location histories or licensed raw feeds. Use environment variables and ignored local .env files.

## Standards
Python 3.12+, FastAPI/Pydantic, typed public functions, Ruff lint/format and strict mypy for app code. Run from root:
`python -m pip install -r backend/requirements-dev.txt`
`python -m ruff check .` / `python -m ruff format --check .` / `python -m mypy` / `python -m pytest -q`.
Add behavioral tests for safety, API contracts and failure paths; avoid tests that merely mirror implementation.
Introduce dependencies only in their scheduled phase. Future clients use React Native/Expo and React with strict TypeScript, linting, formatting and component tests when introduced.
Record architecture decisions in docs/DECISIONS.md. Do not claim a planned feature is implemented. No deployment or payment integration without its phase gates.
