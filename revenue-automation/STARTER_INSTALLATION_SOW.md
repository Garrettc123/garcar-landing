# RA-002 — Speed-to-Lead Starter Installation: Scope of Work (Draft)

**Commercial status:** Proposed offer only. Proposed price hypothesis: $2,500. Not a signed agreement or active checkout.

## Objective
Implement one bounded lead intake and staff-routing workflow for a home-service business, with measurable response tracking and a human-controlled exception path.

## Preconditions
- Named business owner and process owner.
- Written statement of work and acceptance criteria.
- Written authorization for each data source and environment.
- Customer-approved test data or synthetic records.
- Named staff recipients and contact permissions if any messaging is later approved.
- Confirmed credentials scoped to the minimum permissions needed; secrets shared only through an approved secret channel.
- Agreed rollback method.

## Included scope
1. One agreed lead source.
2. Input validation and duplicate handling.
3. Staff assignment or task creation.
4. Response-time event capture.
5. Exception queue for failures or missing ownership.
6. Basic operational report.
7. Synthetic test suite and customer acceptance review.
8. Handoff guide and rollback instructions.

## Explicit exclusions
- No CRM migration or broad data cleanup.
- No autonomous estimating, pricing, diagnosis, or job commitments.
- No outbound calls, email, or SMS unless separately scoped, lawful, consent-checked, and explicitly approved.
- No calendar booking, payment collection, refund, or customer record change outside the written scope.
- No guaranteed revenue, conversion, or booking result.
- No paid infrastructure, subscriptions, or third-party spend unless separately authorized in writing.

## Acceptance criteria
- Valid synthetic lead is accepted and assigned according to the agreed mapping.
- Invalid input is rejected with a traceable error.
- Duplicate event does not create duplicate work.
- Retry/timeout behavior is bounded.
- Failure enters an exception queue and is visible to the process owner.
- Authorized operator can pause the workflow and use the documented manual fallback.
- Metrics reconcile to the test event set.
- Customer signs off on the tested scope before any production cutover.

## Change control
Any additional source, field, workflow, message, integration, or permission is a change request. Work does not expand automatically.

## Security and data
- Data minimization and purpose limitation.
- No production customer data before written permission.
- No credentials in source code, chat, or logs.
- Retention/deletion and support responsibilities must be agreed.
- Production design must pass applicable security review.

## Commercial terms to finalize before signing
Customer legal name, authorized signatory, final price, taxes, schedule, support window, payment terms, warranty/limitations, data-processing terms, confidentiality, termination, and dispute terms remain to be agreed. No placeholder is to be treated as a binding contract.

## Completion record
- Version/commit:
- Test evidence:
- Customer acceptance:
- Production cutover approval:
- Rollback reference:
- Payment verification:
