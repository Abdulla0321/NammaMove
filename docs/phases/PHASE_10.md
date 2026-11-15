# Phase 10 ? Deployment and pilot release

Status: Planned; not implemented.

## Updated integration/pilot gate (2026-11-14; design only)

The limited Bengaluru pilot must validate only explicitly enabled modes and authorized wallet/payment/operator integrations. Review QR/scanner trust, check-in/out and interrupted-journey reconciliation, reservation/debit/refund/settlement separation, consent and data retention. No academic demo entitlement is a genuine BMTC/BMRCL/provider ticket, and a wallet debit is not evidence of bank settlement. Require genuine partner evidence, security/rollback/support readiness and all applicable prior gates; the [PRD v1.1](../PRD.md) amendment authorizes no deployment or real payment activation.

## Prerequisites
All applicable phase gates accepted; source/provider permissions and security/privacy review complete.

## Implementation tasks
- [ ] Build production Docker artifacts and independently version OTP graphs/models
- [ ] Introduce reviewed dependency locks, vulnerability and secret scanning, and artifact provenance
- [ ] Configure staging then production CI/CD, TLS, managed secrets and migration gates
- [ ] Run limited Bengaluru pilot with feature flags, coverage limitations and measured SLOs
- [ ] Practice rollback, backup restore and disaster recovery; document ownership and escalation

## Expected deliverables
Staging/production deployment, approved pilot, release checklist and recovery evidence.

## Edge cases
Failed migration; bad graph/model; revoked feed permission; leaked key; provider downtime; rollback against newer schema; failed mobile release.

## Automated tests
Container smoke tests; staging end-to-end journeys; security scans; migration compatibility; canary metrics; rollback and disaster-recovery drills.

## Completion criteria
No unresolved critical security defects; pilot authorization and SLO evidence recorded; tested rollback/restore; live claims match coverage and safety gates hold.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
