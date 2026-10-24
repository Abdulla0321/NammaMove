# Phase 08 ? Payments and ticketing

Status: Planned; not implemented.

## Prerequisites
Phase 01 identity/audit and Phase 04 clients; provider agreements, sandbox and applicable legal review.

## Implementation tasks
- [ ] Integrate authorized payment/ticket adapters without storing card credentials
- [ ] Implement idempotent orders, payments, tickets, refunds and auditable ledger transitions
- [ ] Verify webhook signatures and replay windows; confirm provider success before entitlement
- [ ] Implement ticket expiry, QR validation, settlement reconciliation and explicit offline restrictions
- [ ] Add receipts, refund support and role-protected operator actions

## Expected deliverables
Sandbox checkout, verified ticket issuance, ledger reconciliation and support runbooks.

## Edge cases
Duplicate/out-of-order webhook; timeout after charge; failed charge; partial refund; QR replay; expired ticket; provider outage.

## Automated tests
Sandbox contracts; forged webhook rejection; idempotency/concurrency tests; ledger invariants; duplicate issuance prevention; refund/reconciliation replay.

## Completion criteria
No ticket before verified provider success; retries cannot double-charge; ledger reconciles; provider approval precedes production.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
