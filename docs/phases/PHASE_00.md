# Phase 00 ? Foundation and project setup

Status: Implemented locally; evidence in ../PHASE_STATUS.md.

## Prerequisites
Existing Git repository and original simulator.

## Implementation tasks
- [x] Inventory all files, APIs, dependencies and gaps; audit for Replit and secrets
- [x] Flatten starter wrapper preserving source and Git history
- [x] Separate runtime/dev dependencies and configure pytest, Ruff and strict mypy
- [x] Add Windows startup guide, environment examples and read-only CI
- [x] Publish all roadmap and safety specifications

## Expected deliverables
Root layout, audit, CI, Windows guide and eleven phase specifications.

## Edge cases
PowerShell activation blocked; missing optional services; missing/stale GPS; unverified closure; unreachable route; negative telemetry age.

## Automated tests
Seven original routing regressions plus HTTP planning, disruption, health/network, status boundaries and input rejection; lint, format and type gates.

## Completion criteria
All local quality checks pass; original route assertions preserved; no real secrets or Replit dependency found; hosted CI awaits push.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
