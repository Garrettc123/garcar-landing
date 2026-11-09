# Garcar Landing — Revenue Funnel Operations

This repository contains public-facing landing assets. **A published page is not a CRM record, buyer inquiry, completed payment, or proof of fulfillment.**

## Canonical buyer-facing catalog (November 2026)

Primary: https://garcar-followup-review.vercel.app/
Products: https://garcar-followup-review.vercel.app/products/

| Offer | Price | Buyer routing | Fulfillment gate |
| --- | --- | --- | --- |
| Lead Follow-Up Review | $497 once | /products/follow-up-review/ | Checkout permitted only after verifying current link and deliverability; one-list prioritized callback plan; 48-hour target conditional on payment, usable data and agreed scope |
| AI Automation Audit | $299 once | /products/automation-audit/ | Checkout permitted only after verifying current link and delivery |
| Lead Backup Installation | $2,500 once | /products/lead-backup-installation/ | Written scope, compatible systems, capacity and acceptance criteria before payment |
| Callback Clock Management | $497/month | /products/callback-clock/ | Scope and capacity before subscription |
| AI Growth Engine | $1,497/month | /products/ai-growth-engine/ | Scope and capacity before subscription; do not promise autonomous full-business execution |

Verified Stripe payment links on 2026-11-07 (recheck before customer use):
- $497 review: https://buy.stripe.com/8x2eVddjf0hQ86Tf0f43S2h
- $299 audit: https://buy.stripe.com/14A5kD3IF9Sqdrd05l43S2l

## Digital products — do not route to paid checkout yet

Four owner-built ZIP deliverables were reported complete and SHA256-verified on 2026-11-07: prompts/SOPs ($27), written mini-course ($79), Operator Toolkit ($149), and Repo Atlas read-only workflow kit ($97). Local delivery-service tests passed, but **remote test-mode payment → private authorized download → transactional email has not been verified end to end**. No automatic fulfillment or immediate-download promise. Track https://github.com/Garrettc123/garcar-payments/issues/20. Any actual paid order requires urgent private manual fulfillment review, purchaser/item verification and no duplicate charge.

## Free, local CSV lead audit

https://garrettc123.github.io/garcar-landing/free-lead-audit.html

The analyzer operates in the buyer's browser. It is not a server upload or verified lead capture. Its voluntary summary-email action opens the buyer's email client; count a prospect only when a real inbound message is received. Suppress DNC and do not claim the tool proves a missed phone call.

## Operational safety and measurement

- Buyer intent must come from a real reply, accepted scope or documented request; CRM stages and newsletters alone do not qualify.
- Match one prospect to one best-fit offer. Do not send unsolicited mass outreach.
- Prepare at most two qualified personalized drafts daily; owner approval required before sending.
- Count collected revenue only from independently verified succeeded live Stripe payment IDs; deduplicate by PaymentIntent.
- Keep checkout, refunds, subscriptions, paid bids, production deployment and outbound messaging approval-bound.
- No sensitive client contact lists through public forms; use agreed secure intake.
- Review Stripe payout/balance status separately from successful payments.
- Do not use the legacy $197 audit, old plan keys or older checkout contract below as current canonical product pricing. Historical checkout code may still exist and requires an explicit migration audit before reuse.

## Development checks before promotion

1. Verify all five service landing routes and actual Stripe product/price associations.
2. Test remote digital delivery in Stripe test mode, including authorized download, real email delivery, refund revocation and idempotent webhooks.
3. Check current production payout constraints without assuming successful settlement.
4. Verify privacy/suppression and one-per-buyer deduplication in the daily revenue loop.
5. Promote only tested changes with owner approval.
