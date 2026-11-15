# Phase 08 ? Payments and ticketing

Status: Planned; not implemented.

## Updated wallet and validation requirement (2026-11-14; design only)

The unified NammaMove Wallet is central intended scope. Before confirmation, atomically verify a configurable minimum (initial INR 500), actual journey affordability and configured reservations/holds for paid legs. Keep balance, held funds, debited funds, pending settlement and provider-settled funds separate. Apply provider-agreed fares/adjustments, refunds and hold release with audited idempotent records. Academic mode uses simulated balances/settlements only: no real deposits/transfers or fabricated genuine tickets. Production requires an authorized wallet/payment partner plus operator agreements; wallet debit is not immediate bank settlement and pending refunds are not received funds.

One demo ticket QR per paid leg: first authorized passenger/ticket/leg/boarding-context scan records CHECKED_IN and IN_PROGRESS and publishes authenticated progress, without debit. Second authorized active-leg/exit-context scan records CHECKED_OUT and COMPLETED, triggers exactly one applicable debit workflow, records settlement separately and activates the next appropriate leg. Verify scanner authority; reject forgery, wrong user/leg and replayed scans/callbacks; handle disconnected checkout as pending reconciliation. Ticket validity and payment state remain independent.

Production metro uses operator-issued QR and authorized gates; bus uses supported operator tickets/validation; auto/cab/bike taxi uses approved pickup/completion (QR only if partner-supported); rentals use authorized unlock/return. Preserve existing entitlements/prior payments and confirm new charges after a Phase 06 revision. Academic early-exit fixed fare may incur the full agreed fare by configurable rule; production applies disclosed authorized fare/refund terms. Extend provider modes only after agreements/data/acceptance. GPS is never proof of boarding/alighting/completion. See [PRD WAL/QR/FARE requirements](../PRD.md) and ADR-027.

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
No genuine ticket without provider-approved issuance authorization; check-in alone never debits; verified checkout/authorized early exit triggers at most one debit; separate settlement/refund records reconcile; provider approval precedes production.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
