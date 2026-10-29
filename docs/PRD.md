# NammaMove — Product Requirements Document

| Attribute | Value |
|---|---|
| Product | NammaMove |
| Document version | 1.0 |
| Updated | 2026-10-29 |
| Status | Requirements baseline for review; not a production acceptance certificate |
| Primary market | Bengaluru commuters |
| Primary client | Android-first React Native / Expo application |
| Supporting client | React / TypeScript commuter web preview, later operations console |
| Delivery sequence | Phase 00 through Phase 10; no dates committed here |

## 1. Purpose and authority

NammaMove helps commuters plan understandable multimodal journeys and, in later phases, recover safely when transport conditions change. Its recommendations must distinguish what is scheduled, observed, estimated, unavailable or simulated, and must consider network impact before automatic rerouting.

This document defines the whole product: users, outcomes, functional requirements, safety constraints and acceptance gates. It consolidates the existing strategy; it does not authorize new provider access, payments, deployment or advancement past a phase gate.

The [master plan](MASTER_PLAN.md) governs delivery order, [phase status](PHASE_STATUS.md) records actual acceptance, and [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md) govern implementation. The [feature matrix](FEATURE_MATRIX.md) distinguishes implemented capabilities from plans. Where older backlog or scenario wording differs from executed evidence, use the latest phase evidence and record any requirement change explicitly. The [historical backlog](PRODUCT_ROADMAP.md) remains a source of future ideas, not a declaration of completed scope.

## 2. Problem and product vision

Commuters need to compare bus, metro and walking connections without piecing together disconnected schedules, unclear fares and uncertain service information. During disruptions, a superficially faster alternative can be infeasible, inaccessible or harmful when many riders are sent onto the same constrained corridor.

The target experience answers: Where can I board? When should I leave? Can I make the transfer? What is known about fare and accessibility? How reliable is this information? If conditions change, what safe alternatives exist, and why are they recommended?

These problems and proposed benefits are product hypotheses. User interviews and an authorized pilot must validate demand and outcomes; no market size, adoption, agency partnership or financial return is claimed.

## 3. Users and responsibilities

| Persona | Need | Product responsibility |
|---|---|---|
| Daily commuter | Repeatable commute with sensible alternatives | Saved places, clear comparisons, scoped updates and understandable recovery |
| Occasional rider or visitor | Simple boarding, transfer and alighting instructions | Search, leg details, local time, transparent data limitations |
| Rider with accessibility needs | Feasible step-free options and usable controls | Source accessibility constraints, explicit unknowns, accessible interface and manual origin |
| Rider with limited connectivity or battery | Useful information without continuous tracking | Consented timestamped cache, clear stale state and later reduced-refresh behavior |
| Moderator / authorized operator | Assess incidents and maintain trustworthy service evidence | Role-scoped verification, expiry, audit and abuse controls |
| Support / platform operator | Diagnose failures without exposing rider data | Privacy-safe health, feed-quality tools, bounded work and recovery runbooks |

Commuter metadata must never grant moderator or administrator authority. Product, engineering, data-rights, privacy/security and operational owners must be assigned before a pilot; specific people are not assigned by this document.

## 4. Goals, boundaries and release definition

### Goals

- Make feasible bus/metro/walk journeys easy to find, compare and understand.
- Make evidence quality and uncertainty visible rather than imply unsupported certainty.
- Preserve usable manual and offline paths when permission, feeds or services fail.
- Introduce trusted disruption recovery and predictive assistance only after their evidence gates.
- Protect identity, saved places and location information throughout the journey lifecycle.
- Measure rider outcomes and aggregate network effects before scaling recommendations.

### Scope by release maturity

| Boundary | Scope |
|---|---|
| Engineering preview | Independently authored synthetic transit/geographic fixtures, genuine local Auth/API/OTP integration, Android-first client and web preview |
| Authorized Bengaluru pilot | Reviewed source rights, demonstrable current coverage, operationally validated routing/accessibility, accepted client/security/operations gates and explicit pilot approval |
| Later product capabilities | Licensed live feeds, trusted recovery, evaluated ML, authorized payments and full operations tooling in their assigned phases |

The first routing mode set is bus, metro and walking. Cycles, contracted cabs, micromobility, voice interaction and turn-by-turn guidance remain conditional backlog items requiring approved scope, usable data, permissions and independent acceptance. A diagram of endpoints is not turn-by-turn navigation.

### Non-goals and exclusions

No unrestricted scraping, default access to agency datasets, fabricated live transport information, guaranteed arrival, guaranteed cheapest fare or guaranteed accessibility is implied. There is no current production payment service, autonomous incident authority, unrestricted location tracking, city-scale congestion guarantee or approved deployment. Monetization, subscriptions, advertising and commercial settlement terms are undecided and must not be silently added to the rider experience.

## 5. Non-negotiable safety rules

| ID | Rule | Acceptance consequence |
|---|---|---|
| SAFE-01 | Missing or stale GPS means uncertainty; it is never sufficient proof of cancellation | Replay and API tests must demonstrate no telemetry-derived false cancellation |
| SAFE-02 | Freshness, operational status, confidence and incident verification are independent | Contracts and UI retain separate fields/states; a fresh unverified report is not an authorized closure |
| SAFE-03 | Production edge closures require trusted, authorized, independently verified and unexpired evidence | Forged client flags, rumors and expired reports cannot close the network |
| SAFE-04 | Automatic recovery must account for downstream capacity and congestion | Network-impact replay against a no-reroute baseline is required; individual shortest paths are insufficient |
| SAFE-05 | Simulation and cached history must remain visible | No synthetic feed is called live; stale cache is never silently presented as a fresh recommendation |
| SAFE-06 | Infeasible or unsupported advice must not be manufactured | No safe route, unknown fare/accessibility and unavailable providers produce explicit explanations |
| SAFE-07 | Credentials, private keys, raw location histories and licensed raw feeds must not be committed | Secret/data review and ignored local storage are required; public client variables contain no server secrets |

## 6. Core rider journeys

1. **Plan:** onboard, authenticate, choose places or manual origin, choose departure/arrival time, modes, walking/accessibility constraints and preference; submit a validated request.
2. **Compare:** see feasible alternatives with travel/wait time, source fare or unknown fare, walking, transfers, ranking explanation and data labels. Select details before relying on a recommendation.
3. **Understand:** inspect boarding, walking transfer and alighting legs, dates/timezones, source identifiers, geographic endpoints and accessibility limitations. Never infer a validated path from a straight connecting line.
4. **Save:** favorite places, revisit recent searches and explicitly opt into bounded on-device journey retention. Open cached records as timestamped historical information.
5. **Degrade gracefully:** retain manual input after permission denial; show meaningful no-route, invalid-input, expired-session or provider-unavailable states. Offer explicit cached access when available, without inventing updates.
6. **Follow a journey, later:** opt into authorized live information, see freshness and uncertainty, and receive scoped boarding/alighting or service notices where supported.
7. **Recover, later:** receive an explanation of verified disruption impact, compare feasible alternatives and confirm a change. If no safe alternative exists, explain waiting or official-support options without promising emergency response.
8. **Pay, later:** use an authorized provider, obtain entitlement only after verified success, and access receipts/refund support with explicit restrictions.

## 7. Functional requirements

Priority describes the gate for the relevant phase: **Must** blocks acceptance, **Should** needs a documented exception if deferred, and **Conditional** requires an external agreement or separately approved expansion. A future Must is not permission to implement that phase now.

### 7.1 Identity, privacy and user state

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| ID-01 | Must / 01, 04 | Authenticate through Supabase; protect private APIs with verified issuer, audience, signature, expiry and subject | Forged/expired/wrong-project tokens fail; every owned access is authorized |
| ID-02 | Must / 01 | Enforce non-owner/non-BYPASSRLS runtime identity and transaction-local verified user context | Genuine PostGIS RLS/grant/isolation tests pass; no startup table creation |
| ID-03 | Must / 04 | Handle onboarding, sign-in, confirmation-required signup, bounded refresh/retry and sign-out | No retry loop or cross-user display; invalid sessions return to sign-in |
| ID-04 | Must / 01, 04, 10 | Minimize retained data; provide clear-data controls and documented retention/deletion scope | Native cache/session behavior and deletion are tested; external account deletion is not falsely claimed |

### 7.2 Transit data and geographic foundation

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| DATA-01 | Must / 02 | Record source ownership, reviewed license/authorization, permissions, redistribution limits, timestamps, checksum and quality notes | No source activation without reviewed rights; an asserted publisher license alone is insufficient |
| DATA-02 | Must / 02 | Validate and version GTFS stops/routes/trips/times/calendars/shapes and the documented supported profile | Malformed coordinates, duplicates, missing references and inconsistent schedules are rejected |
| DATA-03 | Must / 02 | Retain immutable snapshots, provider/mode isolation and rollback-safe promotion | Invalid or concurrent imports cannot replace the last-known-good active version; genuine database tests pass |
| DATA-04 | Must / 02, 03 | Search stops/routes spatially and report coverage, directions, calendars and transfer references | Real PostGIS queries are tested; catalog identifiers are not assumed compatible with an unrelated graph |
| DATA-05 | Must / 02–05 | Separate scheduled/live/stale/unavailable/simulated classifications and approximate timing | UI/API never upgrade estimates, community schedules or missing feeds to authoritative live facts |

### 7.3 Routing and journey explanation

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| ROUTE-01 | Must / 03 | Build/load reproducible OTP releases from authorized geographic data and GTFS | Pinned inputs/image, provenance, integrity checks, real load/canary and retained-release rollback are evidenced |
| ROUTE-02 | Must / 03 | Plan bus/metro/walk journeys respecting directions, calendars, overnight service, transfers and reachable access/egress | Feasibility tests reject missed connections, invalid schedules and disconnected paths |
| ROUTE-03 | Must / 03, 04 | Support departure-after and arrive-by with explicit timezone/date semantics | Exact request boundaries are enforced; physical duration and initial wait are separate from generalized costs |
| ROUTE-04 | Must / 03, 04 | Offer fastest, cheapest, fewest-transfer and least-walking preferences, with hard accessibility/walking constraints | State bounded-candidate ranking; unknown fares are not zero; unknown accessibility is not confirmed step-free |
| ROUTE-05 | Must / 03, 04 | Explain fare, duration, walking, transfers, source confidence and recommendation tradeoffs | Source fixtures are labeled; no current agency fare guarantee or global-optimum claim |
| ROUTE-06 | Must / 03 | Bound provider work and fail clearly on timeout, invalid response, version mismatch or outage | No silent simulator/stale-graph substitution; sanitized errors and graph identity remain available |

### 7.4 Commuter client and accessibility

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| UI-01 | Must / 04 | Provide Android-first navigation, place search, time/constraint selection, alternatives and leg details | Real-device/emulator end-to-end flow passes, not only a JavaScript export |
| UI-02 | Must / 04 | Present suitable geographic information with an accessible list/diagram fallback | Missing geometry is explicitly approximate; native basemap/key/permission behavior is independently verified |
| UI-03 | Must / 04 | Support favorites, saved places and recent searches with user-scoped clear-data controls | Sign-out/user changes do not expose another user's records; initial storage is device-local, not cloud sync |
| UI-04 | Must / 04 | Offer opt-in timestamped offline journeys, loading skeletons, empty states and meaningful errors | Cache expiry/consent/corruption and permission denial work; no implicit fresh-result fallback |
| UI-05 | Must / 04 | Establish English/Kannada/Hindi localization architecture and accessible controls/layouts | Screen-reader names, contrast, large text, small screens, keyboard/Back/rotation and complete localized safety copy are reviewed before locale acceptance |
| UI-06 | Should / 04, 09 | Provide a React web shell that grows into role-scoped operations tooling | Current commuter/status preview is not described as a completed administration console |

### 7.5 Live information, disruptions and recovery — planned

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| LIVE-01 | Conditional / 05 | Ingest authorized GTFS-Realtime positions, trip updates and alerts with independent event/freshness state | Duplicate/reordered/skewed/spoofed telemetry is handled; missing GPS never cancels service |
| LIVE-02 | Must / 05 | Provide authenticated scoped updates, reconnect/polling fallback, explicit opt-in and low-battery behavior | Unauthorized subscriptions fail; outage and backgrounding/privacy tests pass |
| REC-01 | Must / 06 | Maintain evidence provenance, confidence, independent verification, expiry, resolution and audit | Unverified/expired evidence cannot authorize graph closures; conflicting reports are moderated |
| REC-02 | Must / 06 | Deduplicate/rate-limit reports and protect moderator/operator actions | Abuse, forged-role, rumor-storm and concurrent-report scenarios pass |
| REC-03 | Must / 06 | Replan from reachable boarding/alighting positions with accessibility, minimum benefit, cooldown and rider confirmation | Mid-vehicle, concurrent-disruption, no-alternative and oscillation replays pass |
| REC-04 | Must / 06 | Account for aggregate demand and downstream capacity | Automatic recovery remains disabled until network-impact tests demonstrate the approved no-projected-congestion-increase gate |

### 7.6 Prediction, payments and operations — planned

| ID | Priority / phase | Requirement | Acceptance |
|---|---|---|---|
| AI-01 | Must / 07 | Evaluate ETA ranges, transfer risk and no-show probability against declared non-ML baselines | Temporal held-out tests, leakage checks, calibration and route/operator slices pass; probability is not cancellation proof |
| AI-02 | Must / 07 | Version data/features/models, monitor drift, bound inference and retain fallback/rollback | Missing features or inference outages yield explained baseline behavior |
| PAY-01 | Conditional / 08 | Integrate approved payment/ticket providers without storing card credentials | Agreements and sandbox evidence precede any production integration |
| PAY-02 | Must / 08 | Enforce idempotent payment/entitlement/refund transitions and verified webhooks | No ticket before verified success; retries cannot double-charge/issue; forged/replayed events fail |
| PAY-03 | Must / 08 | Reconcile ledger/provider state; support receipts, expiry and explicit offline ticket restrictions | Timeout-after-charge, refunds, duplicate QR and reconciliation scenarios pass |
| OPS-01 | Must / 09 | Provide audited role-scoped feed, incident, support and privacy-safe observability tools | Role isolation, redaction and actionable owned alerts pass review |
| OPS-02 | Must / 09 | Bound queues/rates/concurrency; exercise replay, load, failure recovery and restore | Incident storms, dependency outages and restore drills meet approved budgets |
| REL-01 | Must / 10 | Use reviewed artifacts, secrets, migration gates, staging, canaries and rollback | Source/security/pilot approvals and restore/rollback evidence precede release; no unapproved live claims |

## 8. Data, architecture and integration constraints

Use a modular FastAPI backend before introducing independent services. React Native/Expo and React/TypeScript clients use validated versioned contracts. PostgreSQL/PostGIS is durable storage; Alembic migrations run explicitly with a separate owner identity. Supabase Auth supplies identity, not client-granted authority. Keep the private application schema outside Supabase's exposed schemas.

OTP owns schedule/street search; application boundaries validate returned feasibility, scope and provenance. Version graphs independently from database schema and later models. Redis is a Phase 05 ephemeral cache/queue, never the sole store for financial records or incident authority. Python scikit-learn/XGBoost arrive in Phase 07 after usable history and evaluation design. Docker and GitHub Actions introduce reproducibility progressively; production deployment belongs to Phase 10.

Domain records include commuters/preferences, transit operators/networks/stops/routes/trips/calendars/snapshots, journeys, vehicles, disruptions/evidence, notifications and audit. Payments/tickets/ledger and ML model lineage are later additions. A schema entity or placeholder does not mean the associated live workflow is implemented.

Preserve legacy simulation API compatibility. Current authenticated routing is `/v1/routing/plan`; the fixture endpoint is opt-in and disabled in production. Current catalog and synthetic OTP data are separate; an approved real-network integration must establish consistent identifier/version mapping and tested coverage before enabling a real pilot. See [database](DATABASE.md), [transit](TRANSIT_DATA.md), [routing](ROUTING.md) and [mobile](MOBILE.md) runbooks.

## 9. Quality requirements and measurement

| Area | Requirement / metric | Gate or measurement policy |
|---|---|---|
| Truthfulness | GPS-attributable false cancellations | Target zero; missing/stale telemetry cannot independently trigger cancellation |
| Feasibility | Valid boarding, service day, direction, transfer and accessibility constraints | Behavioral/property/scenario tests plus source and pilot corroboration |
| Performance | Provisional routing/API p95 under 2 seconds | Declare graph size, hardware, concurrency, cold/warm state and measurement window; fixture timing is not city-load certification |
| Availability | Provisional 99.5% service availability | Define observation window, exclusions and operational owners in Phase 09; evaluate against pilot evidence before making an SLA |
| Prediction | ETA error/range coverage, transfer success and no-show calibration | Predeclare baseline, held-out time windows and slices; numeric acceptance thresholds require review before rollout |
| Incident trust | Verification precision, expiry compliance and abuse response | Establish labeled replay/pilot evidence; no fixed achieved precision is asserted |
| Network safety | Aggregate load delta, capacity violations and reroute oscillation | Compare with no-reroute baseline; reject harmful projected diversion; retain cooldown evidence |
| Accessibility | TalkBack, large text, contrast, focus, target sizing, permission denial and manual input | Native device and language review required; mocks do not certify Android behavior |
| Privacy/security | Ownership isolation, data minimization, secret hygiene and safe deletion | Real RLS/Auth tests, dependency review, device storage validation and release security review |
| Resilience | Backup restore, outage recovery and compatible rollback | Measure recovery time/data loss in drills; RTO/RPO are open decisions, not established guarantees |
| Rider outcomes | Task completion, successful journey/transfer, understandable recommendations and retention | Consent-based pilot research; analytics must not become an unreviewed location-history stream |

Every enabled feature needs unit/contract/failure tests and appropriate integration evidence. Database/spatial/RLS claims require real PostGIS; provider claims require actual services or accurately labeled recorded fixtures. Skipped tests, generated SQL, JavaScript exports and configured CI are not substitutes for real migration/restore, native install or successful hosted runs.

## 10. Scenario acceptance and traceability

The complete [scenario catalog](SCENARIO_CATALOG.md) retains stable S01–S24 and R01–R08 references. Minimum release evidence must include:

| Scenario group | Requirements | Expected result |
|---|---|---|
| S01, S03, S10, S21; R02–R03 | SAFE-01/02, DATA-05, ROUTE-02/03, LIVE-01 | Uncertainty, plausible telemetry and local/overnight calendar semantics remain correct |
| S02, S04–S07, S14, S17, S24 | SAFE-03, REC-01/02 | Only valid authority can activate an expiring closure; combined and abusive reports are handled |
| S08, S09, S13, S18; R01, R04–R05 | SAFE-04/06, ROUTE-02/04, REC-03/04 | Feasible accessible alternatives, reachable alighting, no-safe-route explanation and bounded congestion impact |
| S11, S12, S19; R06–R07 | UI-03/04, ROUTE-06, OPS-02 | Explicit failures, manual origin, stale cache and tested rollback without fabricated freshness |
| S16, S22, S24 | ID-01/02, PAY-01/02/03 | Forged identity/webhooks fail; entitlement and ledger transitions remain idempotent |
| S20; R08 | OPS-01/02, REL-01 | Bounded incident/load behavior, authorized targeted delivery and privacy-safe operations |

Examples for the authored local fixture are A→D at 2026-10-26 07:55 IST (bus/walk/metro, 30 synthetic INR, arrival 08:17), express alternatives (50 synthetic INR, arrival 08:35), A→B bus-only (20 synthetic INR), and a no-route result for A→D at 08:40. These are test vectors, not actual Bengaluru schedules or fares.

## 11. Delivery roadmap and exit gates

| Phase | Deliverable | Exit evidence |
|---|---|---|
| [00 Foundation](phases/PHASE_00.md) | Existing-repository organization, standards, CI and documentation | Preserved regressions, environment-independent startup and quality checks |
| [01 Database/backend/security](phases/PHASE_01.md) | PostGIS schema/migrations, persistent APIs, Auth and authorization | Real migrations/RLS/grants, failure paths, genuine Auth and backup/restore |
| [02 Transit data](phases/PHASE_02.md) | Reviewed-source GTFS imports, spatial catalog, snapshots and coverage | Rights/coverage evidence plus real spatial/concurrent/atomic rollback tests |
| [03 Multimodal routing](phases/PHASE_03.md) | OTP releases, feasible journeys and preference explanation | Actual routing/calendar/direction/accessibility/fault/performance tests at declared scope |
| [04 Commuter clients](phases/PHASE_04.md) | Expo Android app and React web shell | Authenticated end-to-end native selection, offline/permission paths, accessibility/localization and client quality |
| [05 Live tracking](phases/PHASE_05.md) | Authorized realtime workers and scoped delivery | Stable event replay, measured freshness, consent/privacy and no false cancellation |
| [06 Recovery](phases/PHASE_06.md) | Trusted incidents, expiring overlays and recovery policy | Trust/expiry/feasibility/cooldown tests and aggregate network-impact gate |
| [07 Predictive AI](phases/PHASE_07.md) | Reproducible evaluated models and guarded inference | Held-out baseline improvement, calibration, drift/fallback and rollback |
| [08 Payments](phases/PHASE_08.md) | Approved sandbox checkout/tickets/ledger | Verified issuance, idempotency, refunds/reconciliation and provider approval |
| [09 Operations](phases/PHASE_09.md) | Operator console, monitoring, replay and resilience | Owned SLOs/runbooks, load/chaos/restore and safety/security review |
| [10 Deployment](phases/PHASE_10.md) | Staging, controlled release and authorized pilot | All applicable gates, source permissions, security review, canary and tested recovery |

No phase is accepted solely because a branch or pull request was merged. Exceptions such as synthetic Phase 03/client engineering while real-provider gates remain open must be explicitly scoped; they do not authorize a live release.

## 12. Current evidence snapshot and limitations

This snapshot is based on repository evidence, not a fresh execution of the full suite for this document:

- Phases 00–01 have local foundation/database/Auth acceptance evidence.
- Phase 02 implements ingestion/catalog/versioning and audits, but BMTC import entitlement, underlying-content clearance for public use and complete authoritative current Bengaluru coverage remain unresolved. Community data and approximate timetable values are not official/live evidence.
- Phase 03 is verified on independently authored GTFS/geographic fixtures. Bounded-candidate ranking, arrival-padding completeness, real paths/accessibility, city-scale load and production hardening remain limitations.
- Phase 04 records 31 mobile tests, 135 backend tests and 11 real client/Auth/API/OTP checks passing in the latest recorded evidence. Browser Auth preflight required an explicit local gateway fix; this is documented rather than hidden by server-to-server tests.
- Native startup/end-to-end, TalkBack, native storage lifecycle, maps, complete Kannada/Hindi translation and signup delivery/deep links remain acceptance gaps. On 2026-10-29, USB authorization/forwarding and backend/Auth/OTP health were checked, but the phone smoke test was blocked by mismatched Expo Go and unavailable Metro. A connected phone and exported bundle are not a passing native smoke test.
- An upstream Expo CLI/Zod dependency advisory and hosted CI verification remain open in the recorded Phase 04 evidence. This document does not re-evaluate advisory status or claim a clean security audit.
- Phases 05–10 remain planned. No live Bengaluru coverage, congestion-safe automatic recovery, accepted predictive model, production ticketing or approved deployment is claimed.

Consult [phase status](PHASE_STATUS.md), [Phase 02 audit](PHASE_02_ACCEPTANCE_AUDIT.md), [source registry](DATA_SOURCES.md) and [Phase 04 evidence](evidence/phase04-mobile.json) for provenance and measured limits.

## 13. Dependencies, risks and open decisions

| Dependency / risk | Required decision or mitigation |
|---|---|
| Agency rights and source continuity | Establish permitted import, use, refresh and redistribution; define behavior after revocation |
| Authoritative coverage and usable geography | Approve a documented geographic/mode pilot boundary and identify excluded areas/services |
| Schedule, accessibility and fare authority | Define verification sources and freshness; preserve unknown/approximate values until substantiated |
| Realtime reliability | Obtain authorized feeds and validate event semantics before displaying live claims |
| Native platform support | Decide supported Android versions/device matrix and validate matching Expo/runtime, storage and accessibility |
| Maps and commercial providers | Review keys, restrictions, terms, costs and data-sharing behavior before enabling external integrations |
| Incident authority and liability | Assign verifier/moderator responsibilities, escalation, evidence expiry and rider-safety wording |
| Aggregate rerouting model | Approve demand/capacity assumptions, replay baselines, rejection thresholds and uncertainty policy |
| Privacy, retention and analytics | Approve consent, deletion/account lifecycle, retention periods, backups and minimal success instrumentation |
| Service objectives | Approve workload-based SLO windows, recovery budgets and operational ownership before promising them |
| Predictive-model scope | Establish usable history, baseline, evaluation thresholds and permitted feature retention |
| Payments/business model | Obtain provider agreements, support/refund policy and commercial approval; no revenue model assumed |
| Dependency security and supply chain | Resolve/review compatible fixes, locks, scanning and artifact provenance before release |
| Resourcing and schedule | Assign owners and estimates per accepted phase; no invented launch date or budget |

## 14. Product acceptance and change control

A product release requires evidence for every enabled Must requirement, approval or a documented exception for each Should, and explicit authorization for every Conditional integration. Exceptions cannot waive the non-negotiable safety rules or turn missing source rights into acceptance.

Before an authorized pilot, complete real-data rights/coverage review, native end-to-end and accessibility acceptance, security/privacy/dependency review, all applicable integration tests, monitoring/support ownership and successful rollback/restore drills. Release notes must state actual geographic/mode coverage and distinguish disabled future features.

Changes to modes, source rights, trust authority, retention, financial behavior, SLOs or release gates require a PRD update and a linked architecture decision where relevant. Update the feature matrix and phase evidence with actual results. Do not commit credentials or raw rider/provider data as proof. Approval of this requirements document is separate from authorization to deploy, merge or begin the next phase.
