# Garcar Enterprise — Lead Follow-Up Review landing page

This repository contains buyer-facing static web pages and a locally runnable lead-list self-check. The proposed canonical homepage is on the draft commercial PR; it is **not a verified production release**.

## Canonical commercial offer

- **$497 Lead Follow-Up Review:** one buyer-authorized CRM CSV export; scope, evidence-backed callback reasons, prioritized CSV, and written summary. Target turnaround of 48 hours *after* complete intake and scope confirmation.
- **$2,500 Callback Clock installation:** separately scoped implementation of follow-up/back-up rules in the buyer's existing workflow.
- **Review credit:** a verified paid $497 review may be credited against a $2,500 installation ($2,003 remaining before agreed adjustments). Do not direct an existing review customer to the full-price installation payment link; confirm the receipt and issue a correctly adjusted invoice.
- No guaranteed revenue, automatic outbound messaging, automated fulfillment, or CRM migration is claimed.

## Actual checkout implementation

`checkout.html` contains direct hosted Stripe Payment Links. It **does not currently call** `/create-checkout-session` or use a `?api=` override. Do not describe payment creation, webhooks, lead intake, or fulfillment as verified solely because static checkout links exist.

Verified live-account link states during the November 18, 2026 audit:
- $497 review: `https://buy.stripe.com/8x2eVddjf0hQ86Tf0f43S2h`
- $2,500 installation: `https://buy.stripe.com/14AdR95QN3u2af14lB43S2j`

The static `checkout.html` also contains an active, alternative full-price installation link. Both must lead to the same properly scoped product, and neither automatically deducts a previously paid review.

An active link is **not** proof of successful charge processing, webhook verification, fulfillment, or payout eligibility.

## Buyer-data safeguards

- Public qualification requests must not include customer records or lead PII.
- Agree on a secure, authorized transfer method before receiving any CSV.
- Label missing timestamps or contact evidence as unknown, not as confirmed missed calls.
- Keep all outbound calls, email, SMS, CRM writes, and payment adjustments behind explicit owner approval.

## Pre-release checklist

1. Confirm the existing draft PR's scope, pricing, and mobile usability.
2. Verify the production host and actual public page reachability.
3. Validate a signed Stripe test webhook, replay/idempotency handling, and traceable fulfillment receipt without live charges.
4. Confirm secure buyer intake, refund/support policy, and a manually monitored delivery procedure.
5. Configure any required GitHub deployment/environment protection; obtain owner release approval before merging or advertising the funnel.

See `commercial/LAUNCH_READINESS.md` for the full readiness inventory.
