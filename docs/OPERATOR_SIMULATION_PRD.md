# NammaMove operator simulation and connected journey PRD

**Version 1.0 · 18 November 2026 · Proposed for review by both maintainers**

This document specifies the operator and simulation subsystem and its handoff to the passenger application. It elaborates the existing [NammaMove product PRD](PRD.md) and [master plan](MASTER_PLAN.md). The repository's phase gates continue to govern live data, production release and payment acceptance. Requirements below describe the target unless marked as repository evidence.

## 1. Product outcome

A rider enters a Bengaluru pickup and destination, compares feasible ways to travel, picks an itinerary and starts one connected journey. The passenger map immediately shows the starting point and route. The active marker moves with the journey clock. At a transfer, the rider sees what to do, where to board and an estimated wait. An assigned driver or station validator confirms boarding and exit. A unified wallet handles the agreed fare and gives the rider one receipt. Operators manage their assigned vehicles and trips, and supervisors trace every movement, validation and fare effect to the related journey and leg.

The first reference journey starts near Whitefield, reaches a metro station by walking or taxi, passes through Majestic and ends at KSR Bengaluru. A simulated BMTC itinerary provides a comparison when feasible. Taxi, BMTC and metro stand for distinct simulated operator adapters. Ola, Uber and Rapido partnerships or live supply are later provider integrations subject to authorization.

### Ownership

| Surface | Accountable maintainer | Responsibilities |
|---|---|---|
| Passenger mobile and product web | Passenger-app maintainer | Landing and sign-in, route comparison, confirmation, moving map, passenger notifications, payment explanation, passenger ticket and receipt |
| Operations web and validators | Simulation maintainer | Fleet and shift operations, scenario control, driver or station screen, QR scan results, vehicle history, reconciliation and audits |
| Simulation service | Simulation maintainer | Provider adapters, dispatch, schedules, deterministic motion, tracking IDs, position history and health |
| Journey and wallet contracts | Both | State transitions, idempotency, identity mapping, shared API schemas, trip and fare ownership, fixtures and integration acceptance |

Both maintainers approve the shared contract and its breaking changes. The passenger team owns presentation and passenger identity integration. The simulation team owns vehicle truth in simulation mode. The journey service owns leg state, and the ledger owns wallet balance and financial state.

## 2. Repository audit and gap

This is a source audit of the working checkout, including the operator simulation files present locally. It does not assign individual authorship or reproduce the user's browser session.

| Existing code | Observed capability | Integration gap |
|---|---|---|
| [Passenger API client](../apps/mobile/src/api.ts) and [Expo app](../apps/mobile/App.tsx) | Calls the authenticated routing planner and renders itinerary details | Route selection has no connected journey-start request or position subscription |
| [Native route map](../apps/mobile/src/RouteMap.native.tsx) | Shows static leg start and destination markers with endpoint-to-endpoint lines when opened | Needs detailed geometry, active marker, source labels and journey updates |
| [Main FastAPI entry](../backend/app/main.py), [routing module](../backend/app/routing) and [transit catalog](../backend/app/transit) | Persistent APIs, auth and an OTP fixture adapter coexist with versioned GTFS catalog work | Main API and operator service do not share journey lifecycle or a fleet assignment contract. Catalog coverage and rights remain gated |
| [Operator API](../backend/app/simulation/api.py) and [Mapbox adapter](../backend/app/simulation/mapbox.py) | Separately served console and API. Configured street routes can carry Mapbox paths. A paid leg starts moving only after boarding | Fixture legs can lack paths, the browser map has a separate load step, and a waiting leg has no advancing clock until boarding |
| [Operator console](../backend/app/simulation/console.html) and [tracking API](../backend/app/simulation/replay_api.py) | **Choose route** opens the interactive journey. **Start tracked simulation** runs a separate, durable replay and polls positions | Two actions create two lifecycles. A replay does not represent the selected passenger journey. Mapbox rendering can fail while the API still returns data |
| [Tracking store](../backend/app/simulation/tracking.py) | SQLite run definitions, concurrent run UUIDs, reconstructable per-second position IDs | Move shared journey, allocation, event and ledger state to durable, owner-scoped storage. Preserve standalone replay for scenario testing |
| [Realtime ingestion](REALTIME.md) and [evidence](PHASE_STATUS.md) | Existing synthetic ingestion, Redis and durable evidence foundations | Ingestion acceptance does not establish passenger tracking, licensed live coverage or end-to-end integration |
| Operator ticket and ledger flow | Assigned vehicle can accept, scan in, scan out and debit a process-local wallet | Ticket creation and output do not give the passenger app a usable boarding pass. Multi-user identity, durability and settlement are missing |

The source explains the observed behavior. A route can be selected without ever sending movement to the passenger map. In the operator console, a fixture route, map initialization failure, a waiting paid leg, or the separate replay action can each prevent a visible moving marker. The integrated acceptance test must distinguish all four conditions.

## 3. Release scope and priorities

| Release | Required experience | Data and authority |
|---|---|---|
| R1 Connected journey | Select and confirm one itinerary on the passenger app. Open the map with a pin and full geometry. Move the pin, reconnect and finish or transfer. See the same journey ID in the ops console | Mapbox street geometry where configured and reviewed. Versioned synthetic fleet and test transit paths. No financial execution |
| R2 Operator workflows | Multi-vehicle scenarios, concurrent journeys, operator assignment, taxi acceptance and transfer notifications. Reopen the history by ID | Synthetic schedules and supply. Verified staff identities and source-scoped access |
| R3 Academic wallet and ticketing | Reserve demo funds, complete real scan interactions, record a balanced demo debit and payable, issue a rider receipt and reconcile in ops | Simulated INR and demo passes. Provider-specific rules exercised through fixtures |
| R4 Authorized pilot | Approved feed coverage, operational integration, authorized validation and payment arrangements | Licensing, partner, security, accessibility, privacy, financial and release gates from the master plan |

### User experience and routing requirements

| ID | Requirement and acceptance |
|---|---|
| PLAN-01 | Search by typed address or consented device location. Display the resolved origin and destination before confirmation. Support an explicit pin correction. Ask for clarification on ambiguous results and distinguish coverage gaps from upstream failures. |
| PLAN-02 | Return up to four genuinely feasible itineraries across walk, taxi, BMTC and metro. Show total and per-leg fare, estimated duration range, transfers, walk distance, operator, accessibility and provenance. Present cheapest, fastest and low-transfer recommendations where supported. Return fewer options when alternatives are infeasible. |
| PLAN-03 | Obtain walk and road geometry through the street routing adapter. Use network stop, direction, service calendar, transfer and geometry data for transit. Validate walked access distance, stop and station connections, direction, feasible transfer windows and booked fare expiration. Keep synthetic bus and rail labels visible. |
| NAV-01 | **Start journey** on a selected route is the single committed action. A card tap can preview it. On confirmation, create or recover exactly one journey and simulation binding, open the map immediately, draw the route and place the active pin at its first coordinate. A permitted walking leg starts automatically. |
| NAV-02 | For a paid first leg, show the rider at the pickup and the assigned vehicle approaching when available. If the scenario starts with the vehicle at pickup, show the waiting state and boarding action. The onboard marker begins advancing when authorized boarding starts the leg. Vehicle arrival never performs the scan automatically. |
| NAV-03 | Render the complete GeoJSON line in the correct order and coordinate convention. Keep pickup, vehicle and onboard rider identity clear. Follow the active marker until the user pans. The user can recenter. Clearly distinguish rendering, tracking, and connectivity failures. Provide a lightweight text and steps view when tiles fail. |
| NAV-04 | On app recovery, restore the active journey and consume events after the last confirmed sequence. Missing updates display their age and last known position. Duplicates and out-of-order updates cannot move the marker backwards or complete a leg. A new route revision explicitly resets geometry and progress anchors. |
| NAV-05 | On reaching a transfer boundary, keep the previous leg's completed state and show the next stop, direction and estimated departure. A simulated two-minute notification can be generated from a fixture schedule. Suppress duplicate notifications on reconnect. Walking completion requires its applicable confirmation rule. Paid legs require authoritative validation. |

## 4. Fleet, operators and supervisor console

| ID | Module | Required behavior |
|---|---|---|
| OPS-01 | Supervisor control center | Show map and searchable fleet table by provider, mode, assignment, service status, freshness and simulation status. Selecting a vehicle shows public vehicle ID, permitted plate and staff details, route, last position age, run and journey references, and recent events. |
| OPS-02 | Provisioning | Invite or enroll staff, assign a provider and role, assign vehicles and shifts, revoke access and audit changes. Use revocable one-time enrollment or identity-provider invitations. Mask contact fields by default. Existing passwords and scanner credentials are never revealed in vehicle details. |
| OPS-03 | Taxi | Model offline, available, offered, accepted, en route to pickup, waiting, onboard, arrived and released. Time-bound each offer. Concurrent acceptance cannot double-assign a vehicle. Support decline, timeout, reassignment and cancellation with attributable reason codes. |
| OPS-04 | BMTC | Represent route, direction, scheduled trip, stop sequence, vehicle, conductor/validator and capacity. Follow the assigned service path. Use stop context for boarding and exit. Display capacity uncertainty and maintain separate simulated and authorized data sources. |
| OPS-05 | Namma Metro | Model line, direction, station, train run or service context, and station validator. Distinguish station entry, boarding evidence where available and station exit under the authorized operator policy. In academic mode bind validation to simulated leg, service and station context. |
| OPS-06 | Scenarios | Start multiple runs from a deterministic seed and route version. Bound tick rate and duration. Control pause, resume, speed and injected delays when privileged. Label a scenario replay as a replay and retain attributable history for each control action. |
| OPS-07 | Operations and reconciliation | Filter by journey, leg, run, vehicle, ticket, scan or transaction ID. Show trip start/exit, completion, pending actions, holds, debits, payable and settlement. Export authorized audit subsets with permission checks. Handle disputes, exceptions and refunds through new auditable actions. |

## 5. Shared lifecycle and algorithms

**Journey lifecycle** goes from quoted to confirmed and active, then completed or cancelled. A route revision is a versioned transition that changes eligible future legs while preserving past activity. Suspension and reconciliation statuses indicate uncertainty and carry a reason.

**Leg lifecycle** starts at pending, then ready or awaiting assignment. A paid leg moves through assigned and awaiting boarding, in progress, arrived awaiting exit, and completed. Walking can start directly when ready under the journey policy. Cancellation and failure are explicit terminal alternatives. No geometric position directly authorizes a fare.

**Motion algorithm**

1. Normalize every leg to a versioned geometry, a source, a service pattern and timing data. Use timed segments when their indices align exactly. Otherwise distribute movement by cumulative segment distance. Keep dwell and wait intervals explicit.
2. Persist a simulation run, its fleet assignments, scenario seed, effective start, speed and ordered clock changes. Derive progression from authoritative elapsed simulation time. A browser only renders snapshots and does not own the clock.
3. Resolve the active leg or vehicle trajectory and locate the active segment using cumulative offsets. Interpolate between adjacent vertices and clamp at phase boundaries. Keep street and rail geometry distinct. Represent discontinuities as transfer events rather than interpolating through unrelated paths.
4. Produce one canonical position per simulated second, plus exact final and phase-boundary events. Position records identify subject, run, tick, coordinates, speed, heading when meaningful, observed time, source and geometry version. Use a separate event ID for each transition. IDs remain stable under retry and replay.
5. Publish current state plus ordered updates. Interpolate the display between authoritative samples on the same leg and geometry version. At accelerated speeds and during outages, allow display frames to skip while retaining all canonical ticks for replay. Avoid unbounded catch-up and send a replacement snapshot when the resume window expires.
6. Persist state and event publication intent in one transaction. An outbox publishes after commit. Redis serves ephemeral latest-position and delivery coordination. Rebuild replay and current state from PostgreSQL or an approved deterministic trajectory definition when Redis loses state.

**AI** enters after reliable observations. Start with schedule and historical-time baselines. Predict ETA intervals and missed-transfer risk using held-out time windows, report calibration by route and provider, and monitor drift. Expose confidence and fallback reason. Predictions cannot authorize debits, mark cancellation from GPS loss, or close routing edges. Reroute only with trusted verified evidence, reachable alternatives, user confirmation when required, and capacity/congestion acceptance.

## 6. Ticket and wallet requirements

| ID | Requirement and acceptance |
|---|---|
| TKT-01 | The passenger sees an actionable QR pass at the correct paid leg, with route, vehicle or station context, expiry, status and accessibility text. The ticket ID remains an audit/support identifier. It is insufficient as a credential. Short-lived opaque or signed QR presentation proves the issued entitlement within its context. |
| TKT-02 | An authorized assigned scanner sends the QR proof and explicit boarding or exit action with an idempotency key. Check trip, leg, rider binding, scanner role, assignment, action, token validity and timing. Board starts motion and emits an event without charging. Exit completes the leg under its policy and triggers the fare workflow once. Two valid scans may reference the same ticket using distinct action-specific presentation challenges and replay protection. |
| TKT-03 | Scan feedback tells the operator and rider whether boarding succeeded, exit succeeded, the ticket is stale, or the action needs review. Wrong vehicle, wrong station, duplicate, forged and out-of-order requests have tested responses. Offline checkout becomes pending reconciliation with a receipt for the attempted action. |
| WAL-01 | Use integer minor units and INR. Confirm only after checking the configurable initial ₹500 minimum, actual available funds and applicable holds in the same transaction. Show full itinerary estimate and per-leg reservation summary. |
| WAL-02 | An authorized completed paid leg consumes its hold and creates one debit and matching operator payable in an auditable journal. Available, held, captured, refunded, payable and externally settled amounts remain distinguishable. Keep debit and payout statuses independent. |
| WAL-03 | Expire or release unused holds. Changes affecting cost require the rider's applicable confirmation. Refunds and corrections use compensating records with authorization, audit and reconciliation. Passenger UI shows a journey receipt and any pending amount. |
| WAL-04 | Academic balances and receipts carry simulation labels. Genuine wallet funding, externally settled money, provider-issued tickets, metro gate validation and payment webhooks require approved provider agreements and product acceptance. |

## 7. Proposed application and data structure

Keep one repository with independent application entry points and independently reviewable modules. Adopt the existing Python/FastAPI, Expo and PostgreSQL stack. Use React and TypeScript for the planned operations and validator web interfaces, with Node.js for frontend tooling. Keep the existing HTML as a development harness during migration.

```text
apps/
  mobile/                    Existing passenger UI, auth and generated client
  operations/                Proposed React supervisor and fleet console
  validator/                 Proposed scanner and provider staff interface
backend/app/
  auth.py, database.py       Existing identity and database conventions
  routing/, transit/         Existing planning and transit catalog
  realtime/                  Existing source ingestion and freshness
  simulation/                Existing package, expand via domain modules
    providers/               Street, taxi, BMTC and metro adapters
    fleet/                   Vehicle, shift, dispatch and assignment
    runtime/                 Simulation clock, trajectories, position replay
    journeys/               Shared journey commands, state and events
    validation/             Ticket issuance and scanner authorization
    ledger/                 Holds, journal, receipts and reconciliation
backend/migrations/          Additive Alembic migrations
backend/tests/               Unit, contract, concurrency and integration suites
docs/                        Requirements, OpenAPI references and runbooks
```

Refactor as each module acquires a real responsibility. Preserve existing routes and fixture commands while migrating clients. Generate passenger and operator client types from the versioned OpenAPI contract. Commit source, schema, representative synthetic fixtures, sample environment names, test code and startup scripts. Keep tokens, location histories and licensed raw datasets out of source control.

| Entity | Key relationships and invariants |
|---|---|
| RouteQuote and Itinerary | Quote ID, expiry, source versions, ordered legs, geometry refs, fare policy version and amount estimates |
| Journey and JourneyLeg | Journey UUID, rider, quote, lifecycle version. Ordered leg UUIDs carry direction, stop context, assignment, start/exit evidence and geometry version |
| Provider, Staff, Vehicle, ServiceRun | Scoped identifiers, assigned shift, capacity and source; availability and authorized validator context |
| SimulationRun and Trajectory | Run UUID, seed, timing, revisions, mode and geometry, with recorded clock changes and associated journeys and vehicles |
| Position and DomainEvent | Run plus subject plus tick for positions. Event UUID and per-journey sequence for transitions. Coordinates are longitude then latitude in GeoJSON |
| Ticket, Scan and Notification | Ticket UUID bound to paid leg and owner. Scan UUID records actor, action, context and result. Notification ID deduplicates delivery by journey and event |
| Wallet, Hold, JournalEntry and Settlement | Wallet per owner and currency, hold bound to quote or leg, balanced journal lines and unique fare effect per completed leg. Settlement references attributable payables |
| Audit, Outbox and IdempotencyRecord | Actor, entity, request correlation and safe metadata. Outbox written atomically. Idempotency scoped to actor and command, with conflict detection for changed payloads |

PostgreSQL/PostGIS owns durable truth with additive Alembic migrations, private schema and existing RLS and role separation. Redis is rebuildable. Define data rights, map storage permissions, retention and deletion before keeping any rider or provider location history outside isolated test operation. Avoid collecting precise home location beyond the approved trip use.

## 8. Passenger and operator API agreement

The routes below are proposed shared interfaces. Document request and response schema, authentication, domain errors, idempotency, provenance and compatibility before wiring clients.

| Operation | Example contract |
|---|---|
| Plan | `POST /v1/routing/plan` maintains existing compatibility. Extend or add a versioned quote interface for detailed geometries, quote IDs and fare validity |
| Confirm | `POST /v1/journeys` with quote ID, itinerary ID and idempotency key returns journey ID, first leg, optional run ID, initial coordinate, geometry revision and event cursor |
| Recover and subscribe | `GET /v1/journeys/{id}` gives authoritative snapshot. Authorized event stream or cursor polling serves events after a sequence |
| Fleet and simulation | Operator APIs list vehicles, assign staff, manage scenarios and retrieve current position plus paginated run history by ID |
| Validation | Passenger retrieves active entitlement. Assigned validator posts scan action with contextual proof and receives prior result on identical retry |
| Wallet | Passenger fetches balance, holds and journey receipt. Authorized reconciliation reads and resolves operator payables via audited commands |

Use Supabase JWTs for humans and scoped, revocable service credentials for server-to-server component access. A passenger client never holds a fleet-admin key. Provider adapters have separately configured scopes. Use the passenger backend as the integration boundary for the friend team's application. Use streaming for responsive updates where supported and cursor polling as fallback. Include request ID, stable error code, retry hint and relevant IDs in safe error responses. Log identifiers rather than raw tokens or precise rider coordinates.

## 9. Quality, acceptance and delivery sequence

The targets below are provisional until the two maintainers agree a representative device, provider budget and load profile.

| Check | Proposed gate |
|---|---|
| First marker | Visible on an already loaded map within one second of successful confirmation under the test network. Map loading and fallback are independently observable |
| Position delivery | One canonical tick per simulated second and initial snapshots promptly available. In 1× connected tests, p95 event-to-display lag under two seconds |
| Geometry | Marker advances along the versioned line, passes bends, reaches exact endpoints, respects waiting and dwell times, and never animates across a low-confidence gap |
| Restart and concurrency | Two riders and at least two fleet runs can operate concurrently without leaking state or double assignment. Process restart, Redis loss and reconnect recover authorized state and event order |
| Financial integrity | Concurrent duplicate exit calls yield one charge; failed writes leave no partial debit; total debit and credit reconcile after retry, cancellation and refund |
| Accessible UX | VoiceOver/TalkBack labels, keyboard operability, contrast, reduced motion and text fallback. Retain existing English, Kannada and Hindi requirements |
| Deployment | Docker-based local integration, secret-free example config, CI for Python, TypeScript, schemas and cross-service tests. Validate backup/restore and publish migration and rollback runbooks before pilot |

### Work order and evidence needed

1. **Agree the contract and reproduce the failure.** Both maintainers run the same Whitefield fixture and record the passenger tap, HTTP response, map readiness, geometry and positions. Agree selected-route and confirm semantics, event schema, identity boundary and provenance rules. Deliver one accepted fixture, shared schema and failure reproduction.
2. **Ship the connected map slice.** Start from the existing mobile route-detail screen and simulation engine. Create the durable journey binding, return its first coordinate, draw the same line, and animate on authorized updates. Demonstrate on passenger mobile and ops web with the same journey/run IDs. Exercise cold start, background/resume, missing Mapbox config, late updates and completion. Do not advance until a recording and automated cross-service test show movement.
3. **Add transfers, providers and fleet ops.** Wire walking, taxi, BMTC and metro fixtures in sequence, ETA notices, direction, stage and fleet controls. Accept multiple concurrent runs, reject cross-provider actions and preserve complete position history across restart.
4. **Connect durable demo tickets and wallet.** Add staff/scanner provisioning, passenger pass, boarding and exit, holds, debit/payable, receipts and reconciliation. Test invalid scans, replay, insufficient funds, connection loss and duplicate charges.
5. **Verify release readiness.** Publish full integration instructions and versioned migrations. Run real Mapbox/browser/device acceptance with configured credentials, confirm data rights and conduct load, privacy, accessibility and failure drills. Accept partner and payment integrations only through the master-plan gates.

**End-to-end reference acceptance.** A rider confirms Whitefield to KSR. The passenger map immediately renders the start pin and a moving first leg. The supervisor sees the same trip and vehicle IDs. Near the transfer, the rider receives one timely boarding notice. An authorized scanner boards the rider using the active QR pass. The marker moves on the assigned route. Exit completes the applicable leg and debits the demo wallet once. The rider reaches KSR, receives a receipt, and the supervisor can retrieve the run, position history, scan and balanced ledger entries after a restart.

### Decisions for both maintainers

- Confirm whether a route card tap previews or selects, and retain **Start journey** as the single confirmation in either UX.
- Confirm the exact passenger web surface as well as mobile, and the first browser/device pair for evidence.
- Choose the approved transit-path and schedule sources and who maintains source rights and versions.
- Approve pilot transfer, cancellation, accessibility and fare policy by provider. Decide operator settlement frequency and exception ownership with authorized partners.
- Confirm clock defaults for classroom use and which users can launch, pause or accelerate a scenario.

### First implementation handoff

> Open the existing Expo route detail and the Python simulation package. Implement only delivery step 2 using the agreed test fixture and existing identity patterns. On Start journey, return and display an authoritative initial coordinate; consume ordered updates and demonstrate visible movement along the full path with the same journey and run in both clients. Include failure recovery, source labels, schema and tests. Record the exact devices, provider mode and verification evidence. Keep ticket and ledger work for its acceptance milestone.
