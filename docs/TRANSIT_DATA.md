# Transit data: Phase 02

## Scope and trust
The static catalog is separate from the seven-edge simulator and the Phase 01 manually maintained catalog. It does not power journey planning, alter disruptions, collect locations, or infer cancellation. There is no OTP, GTFS-RT ingestion worker, Redis, live subscription or Phase 03 implementation.

Each version records provider, publisher, agency/community/synthetic authority, authorization basis, public source/license links, attribution, quality limitations, retrieval/publication timestamps, source version, SHA-256, service coverage and a validation/connectivity report. Publication time may be unknown; retrieval time never substitutes for publication. A manifest is the owner's documented assertion of rights, not an automated legal verification. Never put keys or signed URLs in manifests.

## Source register (reviewed 2026-10-26)

The detailed [rights registry](DATA_SOURCES.md) and [acceptance audit](PHASE_02_ACCEPTANCE_AUDIT.md) supersede any implication that a publisher declaration alone clears all underlying rights. BMTC import eligibility and BMRCL public-deployment content clearance remain unresolved.

| Source | Provenance/license | Qualification and access |
|---|---|---|
| NammaMove tests | Authored synthetic fixtures, CC0 example manifest | Small invented fixed-route network for tests; simulation only, no Bengaluru accuracy claim |
| [Community BMTC](https://github.com/Vonter/bmtc-gtfs) | Publisher declares ODbL; README separately notes BMTC copyright in some contents; derived from Namma BMTC application | Unofficial; incomplete coverage tied to app tracking availability, inaccurate timetables possible. No import or redistribution until content-rights/authorization review. Missing routes do not establish cancellation. Source reviewed at `ee945dc0c21b29193f88e3e1e9af218dd24ea182` |
| [Community BMRCL](https://github.com/Vonter/bmrcl-gtfs) | [Pinned ODbL license](https://github.com/Vonter/bmrcl-gtfs/blob/f402c4c69a5d314320024f84620fa83e909c4188/LICENSE), BMRCL timetable inputs and OpenStreetMap spatial data | Unofficial; intermediate timings estimated, short-loop coverage imperfect. Preserve attribution and source notices; adaptations/public use need ODbL compliance. Isolated internal evaluation only; acceptance outcome is recorded in [phase evidence](phases/PHASE_02.md) |
| Agency BMTC/BMRCL static and realtime | No agency-supplied credentials, contract or authoritative endpoint verified | External acceptance requirement; adapters disabled without explicit configured public URL/manifest. No official live coverage claim |

No raw external feed is committed. Local downloads, manifests and dumps belong under ignored `backups/`. Do not copy restricted datasets into fixtures. Public evaluation summaries may include counts/checksums and source metadata, not raw licensed contents.

## Supported GTFS profile
Reference: [official GTFS Schedule](https://gtfs.org/documentation/schedule/reference/). Root ZIP, UTF-8/BOM CSV, fixed-route bus/metro/tram/rail with `Asia/Kolkata` (`Asia/Calcutta` canonicalized). Imports agency, stops, routes, trips, stop times, calendars, date exceptions, shapes, transfers (types 0-3) and frequencies. BMTC adapter accepts bus type 3; BMRCL accepts metro type 1. Agency URLs/names are source data, never fetched by the importer.

Source IDs are opaque, Unicode NFC/whitespace-normalized and unique within a snapshot. Stop coordinates, references, station parents, direction values, sequences, time ordering, shape distances, frequency overlap and scoped transfers are validated. A missing direction is preserved as unknown, never synthesized as inbound/outbound. Exception-only calendars are supported. Times are seconds from local service-day midnight and may exceed 24 hours (bounded to less than 168 hours). Untimed intermediate stops are preserved only when `timepoint=0`; endpoints need times. No interpolation, frequency expansion or invented schedules occur.

The profile deliberately rejects unsupported Flex/continuous-stop windows and transfer types 4/5. Fares, pathways, translations, feed_info and other optional tables are not imported; their presence creates an optional-table warning. The manifest supplies version/time/provenance instead. Stop hierarchy checks do not establish accessible station paths. Full GTFS conformance, extended route types, official MobilityData-validator certification and route-to-shape map matching are not claimed. A feed needing an unsupported feature remains quarantined until a deliberate implementation and regression test exist.

Budgets: 50 MiB ZIP, 256 MiB declared expanded size, 100 root members, two million CSV rows, bounded field lengths; reject traversal, nested directories, duplicate members, encryption, symlinks, extreme compression and malformed encoding/CSV. Owner-run downloads require credential-free HTTPS, no query/fragment, no redirects, a 30-second HTTP timeout and the ZIP byte budget. This is an explicitly configured maintenance tool, not a public fetch/upload endpoint.

## Import, refresh and rollback on Windows
Use the existing root and venv. PostgreSQL/PostGIS and owner/runtime setup are described in [DATABASE.md](DATABASE.md). Use a separate migration-owner connection in ignored local environment configuration. Never run the API with that connection.

```powershell
Set-Location 'C:\Users\ABDALLAH SHINGERI\Desktop\NammaMove'
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = 'backend'
python -m alembic upgrade head
# Existing default runtime group: run backend/sql/transit_runtime_grants.sql as owner.
# New runtime group: provision using backend/sql/runtime_role.sql after migrations.
python -m app.transit import --manifest .\backups\provider-manifest.json --file .\backups\provider.zip --stage
# Or explicitly download the public URL declared in the reviewed manifest:
python -m app.transit import --manifest .\backups\provider-manifest.json --download --stage
python -m app.transit activate --feed bmrcl:scheduled --dataset '<validated-dataset-uuid>'
# Roll back by activating the retained previous validated UUID for the same feed.
```

Manifest template (replace every example with reviewed source evidence; never label test bytes scheduled):

```json
{
  "provider": "synthetic", "data_mode": "simulation",
  "source_url": "https://example.org/synthetic.zip",
  "license_id": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
  "attribution": "NammaMove authored synthetic fixture; no real transit observations",
  "authorization": "simulation", "authorization_reference": "Authored fixture",
  "publisher": "NammaMove tests", "authority": "synthetic",
  "retrieved_at": "2026-10-26T00:00:00Z", "published_at": null,
  "version": "example-only-v1", "quality_notes": ["Synthetic example only"]
}
```

Scheduled sources must use `open` or `authorized` authorization and non-synthetic authority/provider. Community sources require explicit quality notes. Public URLs cannot embed credentials; future timestamps are rejected. This checks the manifest structure, not the owner's entitlement.

An owner reviews source rights, pins the source revision, downloads to ignored storage, records actual retrieval time, stages, inspects quality/coverage/directions/transfers and then activates. Repeat on a documented provider cadence (initial manual review at least weekly and when source changes; no automatic refresh job yet). Alert on failures/out-of-coverage data; do not discard the last-known-good dataset. Review historical retention and ODbL obligations before public use. Do not delete old versions while readers may still use them.

A transaction-scoped PostgreSQL advisory lock serializes writers per `provider:data_mode`. All inserts and pointer promotion commit together. Failed validation commits only quarantine metadata; SQL/commit failure rolls back the entire transaction. Exit codes: 0 validated/activated, 2 quarantined, 1 configuration/provider/database failure. Unavailable downloads leave the pointer unchanged; their error is returned by the CLI, not stored as a new successful refresh. Idempotence uses byte checksum plus a provenance digest excluding retrieval time, so re-fetching identical content preserves immutable original metadata. Feed last-success timestamps and dataset retrieval timestamps are distinct. No background scheduler is installed.

Simulation and scheduled pointers cannot replace one another. Rollback only accepts a validated version of the same feed. Normalized rows are snapshot scoped. RLS allows verified runtime identities to read retained validated catalog versions; API searches resolve only the active version. This intentional historical visibility lets a request finish against its selected snapshot while another transaction promotes a replacement. Quarantine is admin-visible metadata only. Runtime grants deny all transit writes, including admin API identities. Private `nammamove` remains outside Supabase exposed schemas.

## Search APIs
All require a verified Supabase bearer token. Legacy `/v1/stops` and simulator endpoints remain unchanged.

- `GET /v1/transit/feeds`: active provenance and refresh diagnostics.
- `GET /v1/transit/stops?provider=bmrcl&q=...`: active stop search; optional latitude+longitude, radius_m 1-10000, limit 1-100, offset 0-10000. PostGIS `ST_DWithin`/`ST_Distance` uses generated WGS84 geography and GiST. No SQLite spatial substitute.
- `GET /v1/transit/routes?provider=bmrcl&q=...&stop_id=...`: route names and routes serving a source stop; choose a stop spatially with the preceding endpoint.
- `GET /v1/transit/patterns?provider=bmrcl&route_id=...&service_date=2026-10-26`: ordered source trips/directions/stops and frequency windows; optional service-date calendar/exception filter before pagination. No date means structural patterns, not a claim of today's service. Maximum 100 trips per response; this is a catalog inspection API, not routing.
- `GET /v1/transit/transfers?provider=bmrcl&stop_id=...`: explicit scoped source relationships including prohibited transfers. No inferred walking links.
- `GET /v1/transit/network?provider=bmrcl`: structural directed edges, weak components, unserved platforms and transfer counts. Weak connectivity is not directional reachability, timed-transfer feasibility or safe congestion behavior. Reports are per snapshot, not a combined bus/metro pedestrian graph.

`mode=scheduled` is the default; use `mode=simulation` explicitly for fixtures. Search escapes LIKE wildcards, uses bound SQL and deterministic bounded pagination. A missing active feed returns 503. Responses include dataset ID and provenance. Scheduled data becomes stale after seven days from original dataset retrieval or outside service coverage; stale versions remain available with labels, not silently deleted. This provisional threshold is not a provider SLA. Static schedules always report `realtime_status=unavailable` and `service_status=unknown`. The future realtime contract separately recognizes missing/future/stale observations; none proves cancellation.

## Validation and unresolved gates
Run the root quality commands in [AGENTS.md](../AGENTS.md). Real database tests require a fresh, empty `*_test` database and `NAMMAMOVE_TEST_DATABASE_URL`; genuine Supabase tests use ignored local acceptance config as described in [DATABASE.md](DATABASE.md). Portable tests intentionally use synthetic feeds and SQLite only for nonspatial behavior. See [PHASE_STATUS.md](PHASE_STATUS.md) for executed evidence.

Official source authorization/access, accurate complete Bengaluru coverage, inter-provider transfer/accessibility validation, fresh operational schedules and eventual realtime provider contracts remain external/product gates. A passing small synthetic fixture is not evidence of city-wide feed quality or production performance. No live automatic rerouting is enabled.


## Acceptance-audit additions
[Network coverage evidence](evidence/phase02-network-coverage.json) separates 83 stations, 170 platforms and 235 entrances from the 488 total records. The read-only owner-environment command is `python -m app.transit.audit --dataset <uuid>` with `PYTHONPATH=backend`; it uses an explicit PostgreSQL read-only transaction. Reports distinguish weak and strong connectivity, same-route reverse patterns, reference/time/coordinate integrity and advisory geographic screening from external certification. Synthetic fallback controls and remaining evidence requirements are in the [audit](PHASE_02_ACCEPTANCE_AUDIT.md).

Pattern stop records now preserve source `timepoint` and expose `timing_precision=approximate` for 0 or `source_timepoint` for 1. Dataset metadata states `agency_schedule_accuracy_verified=false`. No current agency schedule certification has been completed; type 1 is not an observed arrival guarantee. The retained real snapshot has all 88,906 stop-time flags at 0. Bounds checks, reverse patterns and a one-component weak graph do not establish all-pairs directional, pedestrian or accessible travel feasibility.
