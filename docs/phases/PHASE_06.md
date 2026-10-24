# Phase 06 ? Disruption verification and recovery

Status: Planned; not implemented.

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
