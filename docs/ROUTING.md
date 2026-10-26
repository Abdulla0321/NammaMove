# Phase 03 synthetic schedule routing

## Scope and source rights
The user's Phase 03 instruction explicitly authorizes fixture-based engineering despite unresolved Phase 02 external data gates. Those gates remain open in [DATA_SOURCES.md](DATA_SOURCES.md) and [PHASE_02_ACCEPTANCE_AUDIT.md](PHASE_02_ACCEPTANCE_AUDIT.md). This work neither accepts Phase 02 nor enables live/official Bengaluru journey planning.

All GTFS trips, fares, stop coordinates and the street grid are independently authored test content. Fixture content is dedicated to CC0-1.0; no actual OpenStreetMap database contents, BMTC/BMRCL rows, raw location histories or copyrighted map images are used. The small PBF encoder writes the [OSM PBF format](https://wiki.openstreetmap.org/wiki/PBF_Format), not copied geographic content. Four fictitious stops near Bengaluru-coordinate values are connected by an invented 164-node street grid: they are not actual places/streets. Seven fictitious trips cover bus, metro, reverse direction, a weekday exception, an after-midnight run and an explicitly inaccessible vehicle.

OTP is pinned to official 2.7.0, Java 21, linux/amd64 image digest `sha256:640870b240ad206d05634e7a066588804c6e23abebf37cbc02b0c9ba66073486`. See the [versioned configuration documentation](https://docs.opentripplanner.org/en/v2.7.0/Configuration/) and [build configuration](https://docs.opentripplanner.org/en/v2.7.0/BuildConfiguration/). This pin has been exercised, not certified for production security; review release support/vulnerabilities before any pilot upgrade. HTTPX was already a runtime dependency; no new Python packages are added.

## Reproducible Windows build
Use Docker Desktop Linux containers and the existing venv. Choose a **new/empty** build directory for every build. Generated ZIP/PBF/graph/report files stay in ignored `backups/` and are not committed. The separate Compose project is `nammamove-routing`, so its lifecycle is isolated from the existing PostgreSQL project.

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
.\.venv\Scripts\Activate.ps1
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
$env:PYTHONPATH = 'backend'
python -m app.routing.fixture --output backups/otp-build-001
$env:NAMMAMOVE_OTP_BUILD_DIR = (Resolve-Path backups/otp-build-001).Path
# Fixed 2 CPU / 3 GiB container limit; Java heap 2 GiB. No builder network.
docker compose -f compose.routing.yaml --profile build run --rm otp-build
# Stop if build failed; never seal a failed build or overwrite an earlier release.
if ($LASTEXITCODE -ne 0) { throw 'OTP graph build failed' }
python -m app.routing.build seal "$env:NAMMAMOVE_OTP_BUILD_DIR"
python -m app.routing.build verify "$env:NAMMAMOVE_OTP_BUILD_DIR"
docker compose -f compose.routing.yaml up -d otp
$env:OTP_URL = 'http://127.0.0.1:18081'
$env:OTP_MANIFEST = Join-Path $env:NAMMAMOVE_OTP_BUILD_DIR 'manifest.json'
# Use the existing non-owner runtime DB and Supabase configuration for the API.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For every subsequent command, stop on a nonzero exit. Container graph loading and Java warmup are separate from steady-state latency: early calls may return 503 until the provider is ready. Do not expose the raw OTP debug/GraphQL service publicly. The FastAPI endpoint is authenticated; the fixture endpoint is disabled when simulation is disabled or APP_ENV=production.

The generator fixes ZIP timestamps and writes canonical LF JSON, making input hashes independent of Windows newline translation. Graph identity hashes the pinned image plus all five inputs. Sealing validates GTFS, input hashes, source stop coordinates, coverage dates and the restricted fixture fare table, then records the actual graph artifact SHA-256. Sealing is an integrity step, not a Java deserializer or a substitute for a successful graph build/load and routing canary. Serialized graph binaries can contain build-specific metadata; reproducibility means identical declared inputs/image and tested behavior, not promised bit-identical Java serialization.

The application verifies the sealed release once when constructing the app. A corrupt/missing release disables the new routing provider without breaking legacy APIs. It never builds/migrates on API startup. Routing manifests must be owner-controlled. Bind OTP and the backend to the same release operationally; the backend verifies local hashes but cannot remotely attest that an arbitrary loopback process loaded that binary. Compose mounts the selected build directory, and acceptance records the actual running image/resource limits. Runtime API users cannot select a server URL or read a manifest path.

## Versioning, release and rollback
Build and canary a new directory on a separate loopback port first, retaining the current container/files. After success, coordinate OTP and backend restart using the same new directory; responses include input-derived graph_id and actual graph_sha256. No automatic graph replacement, live file reload or silent stale-graph fallback occurs. Do not rebuild in a sealed directory. Artifact corruption is detected before constructing a new provider; existing app instances keep their selected manifest until restarted.

Rollback: verify the retained previous release; start/load that graph; set OTP_URL and OTP_MANIFEST together for the previous release and restart the backend. A request pinning the wrong graph_id receives 409 and must replan. A real rollback canary was executed against a separately served prior graph and the current graph remained usable. This is explicit operator rollback, not a zero-downtime production deployment controller. Cold-start pauses and remote graph attestation remain operational limitations.

## Authenticated API
`POST /v1/routing/plan` requires a verified Supabase token. Existing `/journeys/plan` simulation and Phase 01/02 `/v1` contracts remain separate and unchanged. The provider interface takes a typed request and returns a versioned response; trip/route/direction IDs and graph version provide future recovery/update correlation. Realtime updaters and disruption overlays remain disabled.

Example body for the authored fixture:

```json
{
  "origin": {"stop_id": "A"}, "destination": {"stop_id": "D"},
  "when": "2026-10-26T07:55:00+05:30", "arrive_by": false,
  "modes": ["BUS", "SUBWAY", "WALK"], "max_walk_m": 500,
  "wheelchair": true, "max_transfers": 3, "transit_required": true,
  "preference": "fastest", "limit": 5
}
```

A point uses a known fixture stop ID **or** both WGS84 coordinates, never both representations. Unknown stop identifiers return 422. Coordinates/timezones/limits are validated, duplicate modes and extra request flags are rejected. Both departure (`when` earliest) and arrival (`arrive_by=true`, latest deadline) searches are supported. Calendars, date exceptions, previous-service-day overnight runs, travel directions, street access, transfer slack and vehicle accessibility are evaluated by actual OTP. The adapter independently checks chronology, connected endpoints, transfer slack, requested time/mode/walking/transfer limits and rejects inconsistent provider data.

Responses include source attribution/license and OTP release alongside graph hashes, and explicitly report simulation, authored-fixture confidence, realtime unavailable, service status unknown, no disruption overlay and unverified congestion safety. A missing feed never implies cancellation. Static wheelchair constraints exclude unavailable/unknown transit accessibility; authored street wheelchair tags are used by OTP. This is not evidence that a real lift works or a real path is safe.

Each itinerary has scheduled start/end, physical duration, initial wait, elapsed time from requested departure, walk distance, transfer count, source leg IDs and explanations. For the 07:55 query, bus?walk?metro leaves at 08:00 and arrives at 08:17: 17 minutes within the itinerary, five minutes initial waiting and 22 minutes from the requested departure. Generalized routing costs are never added to those timestamps. Arrival-time queries expose no misleading elapsed-from-requested-departure value.

Preferences rank **bounded returned candidates**, not all possible city journeys: earliest arrival/latest departure for fastest, known INR amount for cheapest, transfer count, or walking distance, with time tie-breaks. There is no guaranteed globally cheapest/fewest-transfer/least-walk solution. OTP filtering may omit alternatives before application ranking. In particular application walking limits are post-filters and can produce a conservative no-route result even when an unreturned candidate exists. This limitation is visible in `ranking_scope` and remains a real-network acceptance concern.

Known fares are the authored fixture's integer INR per boarding, derived/checked against GTFS `fare_attributes`/`fare_rules` with zero permitted transfers; this is not a general fare engine, ticket offer or BMTC/BMRCL fare claim. One fixture route intentionally has unknown fare. Unknown is null and cannot rank as free; walking-only is explicitly zero. Products, pass deduplication, zone/discount rules and production quotes are not implemented.

## Boundaries and failure behavior
- Up to four concurrent provider calls per FastAPI process; immediate 503 when saturated. This is not a distributed/global limiter.
- Two-second-level steady-state target; upstream read/connect timeouts are 1.5s, 2 MB response budget, 16 candidates and 64 legs per candidate. No redirects, environment proxy credentials or client-provided GraphQL queries.
- Eligible search interval is two hours. OTP 2.7 produced a reproduced false negative for an arrival deadline just after a feasible connection; the adapter gathers candidates with ten minutes of arrival padding and strictly filters every itinerary to the original deadline and two-hour interval. This bounded workaround is tested but does not establish exhaustive arrival-time optimality.
- The HTTPX timeout is an inactivity timeout plus an elapsed check while consuming chunks, not hard process cancellation of an in-flight Java search. Cold starts and server-side tasks may outlive a client timeout. Review stronger server admission/cancellation and release upgrades before a production pilot.
- No-route/same-location/outside-coverage/disconnected/missed-service cases return explicit no_route reasons. Provider transport/GraphQL/invalid-schedule errors return sanitized 503; graph conflicts return 409. No silent routing through the legacy simulator or an unauthorized graph.
- Only static source schedules are used; no source request flag authorizes cancellation/closures. No automatic incident rerouting, demand assignment, congestion avoidance guarantee or live tracking is introduced.

## Tests, CI and evidence
Portable tests use a response recorded from actual OTP over these owned fixtures. Mock transports are used only for contract/failure boundaries and are not counted as real OTP acceptance. Actual service tests exercise transfer journeys, reverse patterns, holidays, midnight runs, missed connections, arrival deadlines, modes, walking bounds, inaccessible vehicles and four-concurrent-request load. A separate test signs in through genuine local Supabase and benchmarks the actual FastAPI route with no Auth/database/provider overrides.

```powershell
$env:NAMMAMOVE_TEST_OTP_DIR = $env:NAMMAMOVE_OTP_BUILD_DIR
$env:NAMMAMOVE_TEST_OTP_URL = 'http://127.0.0.1:18081'
python -m pytest -q -m 'otp and not supabase'
# Configure real disposable PostgreSQL and ignored genuine Supabase acceptance
# settings as documented in DATABASE.md, then run the complete suite:
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

For repeatable full-API benchmark evidence, set NAMMAMOVE_ROUTING_EVIDENCE to an ignored JSON output path and run the complete test suite with actual service environments enabled. Only non-secret aggregate graph/timing data is written. The CI job builds/loads real OTP from authored inputs and runs OTP tests that do not require Supabase; genuine Supabase interoperability is local opt-in. Hosted CI execution, Linux/Python 3.12 backend execution and actual Bengaluru pilot load are not claimed from Windows results.

Measured local results and exact hashes are in [PHASE_STATUS.md](PHASE_STATUS.md) and [evidence](evidence/phase03-routing.json). The build's connectivity messages describe one authored island with no removed edges; two graph-wide street-safety normalization notices remain in ignored build reports. They are not real network quality certification.
