# Full product backlog (phased; not currently implemented)

## Moovit-class baseline
Journey search across bus, metro, walking, cycles, contracted cab and micromobility; GTFS timetable and transfer handling; live position and ETA when licensed feeds permit; turn-by-turn and accessible navigation; boarding and alighting alerts; favorited commutes; service status; offline cache; multilingual interface; ticketing and QR validation subject to operator approvals; route preferences including cheapest, fastest, fewest transfers, minimal walking, step-free and reliability.

## Bengaluru-first differentiators
- Bus no-show probability with live/stale/unavailable separated from service cancellation.
- Transfer survival probability and replan before missed connection.
- Road closures, metro outages, flood and pedestrian-access alerts.
- Crowd-sourced incident reports with source provenance, abuse prevention, consensus, operator confirmation, expiry and moderation.
- Network-aware rerouting and congestion externality estimate; randomized distribution only among safe comparable options.
- Explainable recommendation messages: reason, confidence, savings, extra walking and fare impact.
- Delay ranges rather than fabricated precise ETAs; confidence-based departure suggestions.
- Offline emergency guidance and low-battery reduced refresh mode.
- Kannada/Hindi/English interaction, voice and accessible large-text UI.
- Operator dashboard, simulation and data-quality metrics; event demand/crowding forecasting.
- Financial receipts, secure tickets and integrated settlement only after provider authorization.

## Scenario matrix
1. Bus GPS stale: show stale timestamp, uncertain service, use schedule with qualifier.
2. Bus cancellation operator-confirmed: invalidate affected service, replan and alert.
3. Bus 20m late but moving: revise ETA and calculate chance of missing transfer.
4. Road blocked verified: remove blocked edges; reroute from reachable current position.
5. Road blocked unverified: annotate risk, validate report, do not assert closure.
6. Flash flood: avoid verified unsafe walking links and underpasses.
7. Metro outage: avoid affected stop sequences while respecting station accessibility.
8. One alternative overcrowded: penalize, distribute demand, include capacity uncertainty.
9. Zero alternatives: say so clearly and provide safest waiting/official support option.
10. GPS spoofed/implausible: reject or quarantine suspect telemetry.
11. Feed outage and backend outage: fall back to timestamped cached schedules.
12. Passenger offline/low battery: cached itinerary and low-update mode.
13. Route replan oscillation: minimum benefit and cooldown before notifying again.
14. Report abuse: rate limits, source reputation, moderator review, expiry.
15. Missing accessible lift: reroute only onto confirmed accessible links.
16. Payment failure: no ticket issuance until verified payment settlement.
17. Two incidents at once: apply both constraints and compute alternatives.
18. Passenger on vehicle mid-diversion: replan from likely next feasible alighting stop, not arbitrary road point.
19. No GPS permission: support manually chosen stops, avoid live tracking.
20. Dense incident storms: bounded computation, targeted notifications and graceful degradation.

## Quality gates
Tests for route direction, incident verification, feed uncertainty, capacity penalties, geospatial constraints, transfer timing, data provenance, permissions, localization, performance, accessibility and safe fallback. Define and measure p95 latency, ETA error, alert precision and false cancellation rate in live pilots.
