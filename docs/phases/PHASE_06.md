# Phase 06 ? Disruption verification and recovery

Status: Planned; not implemented.

## Updated recovery requirement (2026-11-14; design only)

Use authorized verified disruptions or sufficiently supported delays affecting remaining legs. Identify the next safe reachable exit/onward pickup; never suggest exiting a moving vehicle. Preserve preferences and hard accessibility. Compare remaining time, additional/total projected fare, walking, transfers and modes; require explicit accept/reject. Rejection preserves the current journey. Acceptance retains original/completed/current legs, purchased entitlements, incurred/remaining fares and timing in an auditable revision; use operator-supported early exit and confirm any new charges/entitlements. Never assume a pending refund arrived. Academic synthetic fare contracts may configure full agreed fixed fare on early-ended rides; production uses disclosed authorized operator rules. Actual check-out/debit/refund orchestration stays Phase 08. No GPS-loss rerouting; cooldown and aggregate network-capacity gates still apply. See [PRD](../PRD.md) and ADR-027.

## Prerequisites
Phases 03?05 operational; moderator/operator roles; capacity baseline.

## Implementation tasks
- [ ] Store provenance, confidence, observed time, authorized verification, expiry and resolution separately
- [ ] Add deduplication, abuse limits, moderation and audited transitions; client flags never authorize closures
- [ ] Replan only at feasible boarding/alighting points with accessibility, minimum benefit and cooldown
- [ ] Estimate aggregate demand/capacity impact; reject or throttle reroutes projected to worsen congestion
- [ ] Explain confidence, fare/walking changes and no-safe-alternative state; respect rider confirmation

## Expected deliverables
Trusted incident lifecycle, expiring graph overrides, recovery policy and notification audit.

## Edge cases
Rumor storm; conflicting evidence; expired closure; concurrent disruptions; flood; full alternatives; mid-vehicle diversion; oscillation.

## Automated tests
Adversarial trust/expiry tests; combined-incident replay; reachable transfers; cooldown tests; network load simulation versus no-reroute baseline.

## Completion criteria
Unverified/expired reports cannot close edges; absent safe alternatives are explicit; live automatic recovery stays disabled without evidence of no projected congestion increase.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
