# NammaMove Mapbox operator simulation

The operator backend lives in `backend/app/simulation/`. Its API and console support independent, durable simulation runs alongside the interactive QR and simulated wallet workflow. It runs separately from the passenger API.

## Run and demonstrate

### Connected passenger and driver session

From the repository root, install the simulation requirements as shown below and run `./backend/app/simulation/start-local.ps1`. The script initializes the private local replay database and prints separate console, passenger, partner and staff credentials for this session. Keep the terminal running.

1. Open <http://127.0.0.1:8001/passenger> and enter the **Passenger key**. Review available and reserved INR, each route's estimated time and fare, and the per-leg breakdown. If Mapbox is not configured, use the Whitefield to KSR fixture corridor.
2. Open <http://127.0.0.1:8001/driver> in a second tab. Sign in as `taxi-driver`, `bmtc-driver`, or `metro-validator` with the corresponding password printed in PowerShell.
3. Select a passenger route and accept its paid leg in the matching staff view. The passenger screen updates and displays the leg's QR. Import a QR image on a browser with QR detection support, or copy its payload to the validator. Validate boarding. For a mapped leg, exit validation becomes available after simulated arrival. Validate exit and observe the passenger wallet and receipt update.
4. To use live Mapbox requests, set `MAPBOX_ACCESS_TOKEN` in the environment before launching the script and enter an allowed `pk.` browser token in the map panel. The Mapbox adapter retrieves street geometry and estimates. Bus and metro supply, fares, fleet positions and tickets remain simulated.

The friend team's backend can use the **Partner route key** server-side via the `X-Demo-Key` header on `POST /demo/v1/map/routes` or the fixture `POST /demo/v1/routes`. The partner key grants quote access only. The local passenger key covers the single shared demo journey. Staff sign-in creates a 30-minute session scoped to one vehicle or validator. The shared production journey and rider identity integration are separate work.

### Manual setup

From the NammaMove repository root in PowerShell, using the existing backend environment:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/app/simulation/requirements.txt
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:NAMMAMOVE_SIMULATION_DB = Join-Path (Get-Location).Path 'simulation.sqlite3'
.venv/Scripts/python.exe -m app.simulation.init_store $env:NAMMAMOVE_SIMULATION_DB
$env:NAMMAMOVE_DEMO_KEY = [guid]::NewGuid().ToString('N')
$env:NAMMAMOVE_DEMO_KEY
$env:MAPBOX_ACCESS_TOKEN = Read-Host "Enter the Mapbox server token" -MaskInput
$env:NAMMAMOVE_SIMULATION_SPEED = '30'
.venv/Scripts/python.exe -m uvicorn app.simulation.api:app --app-dir backend --host 127.0.0.1 --port 8001
```

1. Open <http://127.0.0.1:8001>. Enter the console key and connect. Enter a Mapbox public browser token in the map panel and select **Load Mapbox map**. A browser token with URL restrictions must allow this localhost origin. The server token stays in the backend environment.
2. Search the default Whitefield to KSR Bengaluru trip or enter Bengaluru address text. Preview the routes on the map. Direct taxi and simulated BMTC use Mapbox road directions. Metro combinations are available near the configured station pair and use Mapbox for first- and last-mile street legs.
3. Load the taxi scanner key and accept the first leg. The console displays its ticket QR. Read an image of the QR on a browser with QR detection support, or paste the displayed token into the scanner field. Validate boarding.
4. Watch the active vehicle move along the route. At **Arrived**, validate exit with the same token. The wallet charges the recorded fare and credits that vehicle's ledger.
5. Repeat for the remaining paid legs. Walking starts automatically when its leg becomes active. Confirm the walk on arrival. At 30× speed, a 10-minute leg takes 20 seconds. Use simulation speed `1` for a wall-clock ride.
6. Use **Start tracked simulation** on a route card to launch an independent run. Choose the clock speed before starting. Multiple runs continue concurrently. Copy the simulation UUID, or use **Find saved runs** to reopen one. Enter a tick and choose **Replay tick** to inspect its position. The simulation store survives a restart. The separate interactive QR journey and wallet remain process-local.

## Simulation backend files

| File | Responsibility |
|---|---|
| `backend/app/simulation/api.py` | Route planning, operator actions, demo QR, wallet and service configuration |
| `backend/app/simulation/mapbox.py` | Mapbox client, geometry validation and interpolation |
| `backend/app/simulation/tracking.py` | Durable run records and deterministic per-second replay |
| `backend/app/simulation/replay_api.py` | Authenticated run creation, lookup and position history |
| `backend/app/simulation/init_store.py` | Explicit SQLite store provisioning |
| `backend/app/simulation/console.html` | Operator and run tracking interface |

Run creation stores an immutable route definition, start timestamp and speed. Each simulated second has a position ID in the form `<simulation UUID>:<tick>`. The terminal sample preserves the exact endpoint. Samples are computed from the durable definition on demand, so closing the browser or restarting the service leaves the intervening timeline available. Valid, geometry-aligned Mapbox durations weight motion along the supplied segments. Legs whose responses omit usable durations use cumulative distance along the same line. Rail is an approximate simulation. The database contains derived trajectories and should be kept private.

## Passenger and operator integration

If the browser address starts with `file://`, open <http://127.0.0.1:8001/> after starting Uvicorn. The console calls the API at the same HTTP origin. A `401` at that URL means the supplied key differs from the server's `NAMMAMOVE_DEMO_KEY`, or the variable was unset when the server started. Set the key and start or restart Uvicorn from the same PowerShell window.

The partner backend can use the contract at <http://127.0.0.1:8001/docs>. An integration key has console privileges in this local build and belongs on the partner server. Each fleet unit has a distinct process-generated scanner credential scoped to that unit's accept and scan routes. Vehicle roster entries are synthetic.

| Method and path | Credential | Role in the demo |
|---|---|---|
| POST /demo/v1/routes | Console key | Returns the three fixture itineraries for the sample corridor |
| POST /demo/v1/map/routes | Console key | Plans Mapbox-backed itineraries and returns a short-lived `plan_id` |
| GET /demo/v1/map/progress | Console key | Returns the active position, progress, phase and simulated seconds remaining |
| POST /demo/v1/simulations | Console key | Starts an independent run from `plan_id` and `route_id`, with optional `speed` from 1 to 120 |
| GET /demo/v1/simulations | Console key | Lists recent run IDs |
| GET /demo/v1/simulations/{id} | Console key | Returns the saved run and leg geometry |
| GET /demo/v1/simulations/{id}/position | Console key | Returns the current position sample |
| GET /demo/v1/simulations/{id}/positions | Console key | Lists elapsed samples after an exclusive tick cursor with a bounded page size |
| POST /demo/v1/journeys | Console key | Checks the ₹500 minimum and reserves the selected itinerary fare |
| GET /demo/v1/state | Console key | Fetches the active journey, ticket, fleet and reconciled demo ledger |
| POST /demo/v1/walk | Console key | Advances a walking leg by explicit confirmation |
| GET /demo/v1/fleet/{vehicle}/credential | Console key | Retrieves that vehicle's scanner key |
| POST /demo/v1/fleet/{vehicle}/accept | Scanner key | Accepts the assigned leg and issues its demo ticket |
| POST /demo/v1/ticket/qr | Console key | Returns a no-cache SVG QR for the active accepted leg |
| POST /demo/v1/fleet/{vehicle}/scan | Scanner key | Validates each explicit boarding or exit action |

Send the credential in the X-Demo-Key header. Book Mapbox routes with both `plan_id` and `route_id`. The latest unbooked plan is bookable for ten minutes. Progress mutations use `journey_id` and zero-based `leg_index`. Scan requests also send `ticket` and `action` (`board` or `exit`). The console polls position once per second with no additional requests to Mapbox. A mismatched credential returns 401. Stale legs, early completion, out-of-sequence scans and repeated exit return 409. Refresh state after a conflict or an uncertain response.

Balance and holds use integer demo INR. The exit transition debits the passenger wallet and records a matched operator credit under the same process lock. The service models one active passenger journey and one shared demo wallet. Taxi and bus move along the Mapbox Directions road geometry using elapsed server time. Bus timing adds a simulated stop allowance. Rail follows an approximate station-to-station line with a simulated ride time. Route fares, provider availability, and vehicle positions are synthetic. Account identity, PostgreSQL-backed concurrent journeys, a licensed transit network, production operator integrations and financial settlement require further work.

The default fixture locations are pinned coordinates. Other addresses use [Mapbox Geocoding v6](https://docs.mapbox.com/api/search/geocoding/) with a Bengaluru bounding box. The simulation keeps derived street itineraries in process memory and does not persist geocoding search results. Street legs use the [Mapbox Directions API](https://docs.mapbox.com/api/navigation/directions/) and the map uses [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/guides/get-started/use-with-cdn/). Without a Mapbox server token, the console labels the local fixture mode. Mapbox credentials and upstream connectivity are required to verify real provider requests.

## Implementation sequence for the shared product

1. Agree on a versioned contract with the passenger-app owner. Define stable route/leg/vehicle IDs, explicit transition events, and a retry contract. Keep integration credentials behind the passenger backend and establish separate passenger and operator privileges.
2. Expand the Mapbox operator planner into a multi-vehicle dispatch engine. Add independent vehicle clocks, depot and service paths, a scenario replay log, and licensed route/stop geometry for bus and metro. Keep real provider telemetry explicitly source-labeled.
3. Add Supabase identities for passengers, staff and supervisors, PostgreSQL tables for journeys, legs and scanner assignments, RLS on private records, and an audited staff provisioning and revocation flow. Rotate credentials and store only verifiers where practical.
4. Extend demo validation with short-lived leg-bound QR codes, dedicated driver and station camera interfaces, and authenticated passenger progress delivery. Use Redis for ephemeral positions and notifications, with PostgreSQL holding authoritative state.
5. Add transactional holds and ledger entries, unique exit/charge keys, reconciliation, cancellation and hold expiry. Exercise retries, overlapping requests, network loss and process restarts before any approved financial or operator sandbox integration.

## Implementation handoff prompt

> In the existing NammaMove repository, extend the local operator prototype with one incremental integration slice. Preserve existing passenger APIs and the synthetic/live boundary. Use the demo contract above as the acceptance fixture. Implement role-scoped identity, durable journey transitions and an idempotent simulated ledger through the existing FastAPI, Supabase, SQLAlchemy and Alembic patterns. Validate the wrong-scanner, replay, concurrent exit and lost-response cases. Update the existing phase evidence with the exact tests run and list the integration prerequisites that remain.
