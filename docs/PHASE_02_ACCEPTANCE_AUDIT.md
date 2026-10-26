# Phase 02 acceptance audit - 2026-10-26

**Decision: full acceptance is not met.** Implementation checks pass, but BMTC import entitlement and a representative BMTC dataset are unresolved. Full current station/schedule/direction/accessibility coverage is not independently certified. BMRCL's community publisher license also must not be mistaken for complete underlying-content clearance for public deployment.

Existing branch: `phase/02-transit-data`. Existing uncommitted work preserved. No Phase 03, commit, push, merge, restricted scraping or new production source activation.

## 1. Source rights and access
The detailed [source registry](DATA_SOURCES.md) records owners/claims, licenses, download eligibility and redistribution constraints for community BMTC, OpenBangalore/geohacker, OpenCity, TUMI and official BMTC/app sources. It distinguishes public metadata retrieval from authorized dataset extraction. No BMTC feed was downloaded or imported during this audit.

The BMTC community publisher's database license and content caveat do not establish a complete NammaMove rights chain. This is **insufficient evidence for the intended import**, not a legal finding that all factual reuse is forbidden. Historical sources have unresolved licenses/dates; an aggregate-statistics license does not transfer to routing data. Official portal access and current TUMI metadata were unavailable; the OpenCity route catalogue direct request returned 403. No restriction was bypassed.

Required closure: a dataset-specific grant/rights assessment covering the intended fields, copy/import/adapt/refresh/public use/redistribution, attribution, exclusions and validity; then a staged representative BMTC import with quality tests. Provider messages have not been sent. Contracts must stay private, with a non-secret evidence reference in provenance.

The existing BMRCL import is only an isolated internal evaluation supported by a documented publisher declaration; public deployment still requires the content/agency rights review recorded in the registry. No copyrighted map or raw transit row is added to Git.

## 2. Authoritative BMRCL comparison
Primary documents inspected on the official website:
- [Schematic route map](https://english.bmrc.co.in/schematic-route-map/) and its [public image](https://english.bmrc.co.in/images/metro/travel-info/sitemapimgkan.jpg).
- [Phase 1/2/2A/2B map](https://english.bmrc.co.in/phase122A2Bmap/) and its [public image](https://english.bmrc.co.in/images/PHASE-1-2-2A-2B.jpg).
- [Agency timetable page](https://english.bmrc.co.in/metro-timings/).
- [Government inauguration release](https://www.pmindia.gov.in/en/news_updates/pm-inaugurates-lays-foundation-stone-of-metro-projects-worth-around-rs-22800-crore-in-bengaluru-karnataka/) dated 2025-08-10, independently establishing the Yellow corridor and sixteen stations at inauguration.

| Item | Actual comparison | Acceptance limit |
|---|---|---|
| Three corridor endpoints | Imported Purple, Green and Yellow endpoints are consistent with sampled official map termini | Map alignment is not proof of current daily operating status; no effective timestamp found on map |
| Interchange samples | Imported shared-parent membership has one Green/Purple station and one Green/Yellow station, consistent with Majestic and RV Road map junctions | Does not certify every platform, passage, minimum transfer time or accessibility path |
| Yellow station count | Imported route has sixteen parent-station identities, matching government inauguration count | This dated fact does not certify today's complete station inventory |
| Station order and directions | Imported longest direction-0 pattern reverses direction-1 at parent-station level on all three routes; no missing direction values | Internal consistency verified; no authoritative mapping from GTFS 0/1 to platform numbers and no exhaustive 83-station alias/order comparison certified |
| Current timetable | Official page returned public HTML/notes but no usable numeric timetable table/images in retrieved content | No fresh agency departure/headway comparison completed; no restricted endpoint reverse engineering or invented times |
| Geographic accuracy | All imported stop/shape coordinates valid and inside a broad advisory Bengaluru rectangle; actual PostGIS tests pass | Official coordinate inventory/footpath alignment not available; bounds and schematic maps do not prove station-level accuracy |

The official overview text also contains stale-looking two-line/zero-count placeholders while the schematic depicts three colored corridors. This inconsistency prevents treating a generic page statement as a fresh operational inventory. The phase map includes additional project corridors; absence from the imported snapshot does not establish that those services are cancelled or unavailable. Current operational status needs dated agency evidence.

Only sampled corridor/interchange/topological facts are corroborated. We explicitly leave full station, direction/platform, schedule and geographic certification open. Public document checksums, scope and false verification flags are included in [coverage evidence](evidence/phase02-network-coverage.json); original images remain ignored local audit material.

## 3. Estimated values and API labels
The retained snapshot is community static data with unknown independent publication time. Its publisher documents derived intermediate timings and imperfect short-loop coverage. Database audit shows **all 88,906 stop-time rows have `timepoint=0`**. No row may be represented as an independently verified observed arrival.

Pattern responses now include additive `timepoint` and `timing_precision` fields: 0 is `approximate`, 1 is `source_timepoint` (not a guarantee of real-world punctuality). Dataset metadata additionally reports `agency_schedule_accuracy_verified=false`; community quality notes and source attribution remain present. These additions preserve all existing fields. A read-only request against the retained real snapshot, using genuine Supabase sign-in and the existing non-owner API login, verified a complete sampled pattern was explicitly approximate. No feed or pointer was mutated. Static realtime remains unavailable and service status unknown. No data was relabeled live, and no schedule value changed.

## 4. Network coverage
Scope: retained **disposable BMRCL evaluation database**, not production or all Bengaluru. The local development database was separately observed to have **zero active static feeds**. Synthetic fixtures are temporary test inputs and are not included in real-provider totals.

| Available source | Operators | Routes | Station records | Platforms | Entrances | Trips |
|---|---:|---:|---:|---:|---:|---:|
| Community BMRCL evaluation | 1 | 3 | 83 | 170 | 235 | 3,279 |
| BMTC | 0 imported | 0 imported | 0 imported | 0 imported | 0 imported | 0 imported |

Zero imported BMTC records means a **data-access gap**, never zero actual bus services or cancellation.

| Imported route | Station identities serving route | Trips | Direction 0 / 1 |
|---|---:|---:|---:|
| Green | 32 | 1,149 | 572 / 577 |
| Purple | 37 | 1,265 | 604 / 661 |
| Yellow | 16 | 865 | 430 / 435 |

There are 85 route-station memberships with two shared interchanges, giving 83 station records. These are source parent identities, not an independently surveyed deduplication. Total `stops.txt` records are 488 across stations/platforms/entrances. Also present: 88,906 stop times, 19 shapes/4,541 shape points, 16 explicit transfer records and 25 trips with times extending past service-day midnight. A year's stated feed coverage is not a guarantee that every route runs on every date.

The checksum remains `c19f56f32ad53525c71191125409dc8dded12dd2cebfc576ad9a4db23a62b8a7`, source revision `f402c4c69a5d314320024f84620fa83e909c4188`, coverage dates 2026-08-17 through 2027-08-17. The retained archive was revalidated and its normalized counts matched the database import.

### Connectivity and known gaps
- 164 unique directed adjacent-stop ride edges and 16 allowed explicit transfer edges; one weak component over served platforms.
- **151 strongly connected components** in the platform graph including those explicit transfers, independently checked with a second mutual-reachability implementation. Weak connectivity must not be reported as all-pairs directional reachability.
- No inferred station passage/platform walking edges, pedestrian network, cross-provider bus/metro transfers or accessibility validation. The component finding concerns this incomplete catalog graph, not the physical metro's operational connectivity.
- No orphan stop-time/trip-service/transfer-stop references, trip time regressions, invalid world coordinates or stop records outside the broad screening rectangle found. The rectangle (latitude 12.5-13.5, longitude 77.0-78.2) is explicitly advisory, not an official boundary.
- BMTC coverage, complete short-loop service, fresh special-event/holiday changes, station aliases and exact platform-direction mappings remain unverified. Official coordinate/accessible-path inventories and current authoritative service evidence are missing.

## 5. Repeatable checks and last-known-good protection
Read-only report command from the root, after activating the existing venv and configuring a maintenance database connection privately:

```powershell
$env:PYTHONPATH = 'backend'
python -m app.transit.audit --dataset '<validated-dataset-uuid>'
```

The CLI starts a PostgreSQL read-only transaction and outputs aggregates, source provenance and explicit verification limits. It creates no tables, imports no data and moves no active pointer. Select the intended database explicitly; the report cannot certify other databases.

Final execution: **87 tests passed, zero skipped** in 16.24 seconds, including eight real PostgreSQL tests and one genuine local Supabase Auth integration test. All original Phase 00/01 regressions remain included. Tests cover directed/weak-versus-strong connectivity, source direction and calendar exceptions, overnight ordering, transfers/station hierarchy/reference failures, coordinate validation, unavailable providers, source/mode separation and approximate-time labels.

Real PostgreSQL tests confirm malformed/quarantined snapshots cannot replace good snapshots, rejected activations cannot cross feeds, normalized-row SQL failure rolls back, concurrent identical refreshes produce one version, revision failure preserves Phase 01, and non-owner API writes are denied. These are real-server tests with synthetic inputs; SQLite/mocks are not counted as spatial/RLS acceptance evidence. Existing genuine Supabase test also exercises protected transit access.

Ruff lint/format, strict mypy (21 application files) and pip dependency consistency pass. Known upstream HTTPX deprecation and generated-geography reflection warnings remain nonfatal. No new schema migration is required by this audit.

## 6. Controlled fallback proposal
If BMTC rights remain unresolved, continue **Phase 02 engineering validation only** with the existing authored synthetic GTFS fixture or additional independently authored fixtures:

1. Use `provider=synthetic`, `data_mode=simulation`, synthetic authority/authorization, explicit authorship and a reviewed project-owned fixture license. Use invented stop/route IDs and schedules; never copy restricted rows, route timings, branding or private histories.
2. Keep manifest notes and every response visibly simulated. Synthetic geographic points are illustrative test coordinates, not surveyed bus stops. Record deterministic fixture versions/checksums.
3. Stage in a disposable test database; activate only an explicit `synthetic:simulation` pointer. Never substitute it for `bmtc:scheduled` or include it in real coverage totals.
4. Exercise malformed/partial feeds, duplicate IDs, holiday/overnight trips, directed disconnected networks, transfer restrictions, unavailable providers and last-known-good recovery with the genuine PostGIS checks.
5. Treat results as pipeline/security evidence only. They do not close source rights, current schedules or city coverage gates. Phase 03 remains blocked until the acceptance requirements are satisfied or explicitly revised by the product owner.

No new synthetic city-scale dataset or source activation was performed by this audit. The proposal does not authorize deployment, public transport guidance or a phase-gate bypass.

## 7. Acceptance matrix and next actions
| Requirement | Audit result |
|---|---|
| Versioned ingestion/search and preserved Phase 00/01 behavior | Complete locally; 87-test run |
| Licensing/source provenance registry | Updated with verified declarations, access failures and precise rights gaps |
| Existing BMRCL data integrity and estimate labels | Verified against retained data; runtime labels improved |
| Authoritative topology comparison | Partial: corridor/interchange samples and dated Yellow count corroborated |
| Full current station/direction/schedule/geographic certification | Unresolved |
| BMTC authorized representative import | Unresolved; no feed downloaded/imported |
| Read-only network coverage report and fault recovery | Complete locally; aggregate report and genuine DB tests |
| Public deployment underlying-content/ODbL clearance | Unresolved; no agency endorsement assumed |
| Full Phase 02 acceptance | **Not met; Phase 03 stays unstarted** |

Next: obtain BMTC's rights evidence/accepted access channel; resolve BMRCL public-use rights and license obligations; obtain dated agency station/platform/schedule/coordinate inventories; perform an alias-reviewed comparison and independently validate transfers/accessibility; then rerun source-specific acceptance checks and record a new decision. Use the controlled fallback while those dependencies are pending. Do not fabricate or edit schedules to force a comparison pass.
