# Phase 01 ? Database and identity

Status: Planned; not implemented.

## Prerequisites
Phase 00 accepted; retention and data ownership agreed.

## Implementation tasks
- [ ] Introduce PostgreSQL/PostGIS, SQLAlchemy and Alembic migrations
- [ ] Define operators, stops, routes, trips, feed snapshots, incidents, evidence, preferences and audit events with stable IDs and spatial indexes
- [ ] Integrate Supabase Auth with JWT signature, issuer, audience and role validation
- [ ] Enforce least-privilege access and RLS where clients access Supabase directly
- [ ] Add transaction, retention/deletion and backup/restore procedures

## Expected deliverables
Versioned schema, database fixtures, authenticated API boundary and restore runbook.

## Edge cases
Expired or rotated JWT; cross-user access; duplicate import; invalid coordinates; interrupted migration; account deletion.

## Automated tests
Migration upgrade/rollback; FK/spatial constraints; unauthorized and cross-user requests; JWT rotation; transaction rollback; retention jobs.

## Completion criteria
Schema recreates cleanly; restore succeeds; authorization tests prove isolation; production verification cannot be set by arbitrary clients.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
