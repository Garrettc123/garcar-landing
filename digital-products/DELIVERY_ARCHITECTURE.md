# Garcar Digital — Sales and Delivery Architecture

## Current verified starting point
- Existing public repository: `Garrettc123/garcar-landing`.
- Existing `checkout.html` and Stripe links are for Garcar service offers, not these digital products.
- Existing README describes `garcar-payments` as the payment API, but its live webhook fulfillment is not established by this repository inspection.
- Do not reuse a service checkout link for a digital guide.
- Do not create Stripe products, prices, subscriptions, or live automations as part of this zero-cost validation stage.

## Phase 0 — validation without paid infrastructure
1. Publish the catalog preview at `/digital-products/`.
2. Use the visible mailto links only for individual inbound questions; do not treat them as an email-list signup.
3. Send one-to-one replies only to people who initiated contact.
4. Record interest manually in a local or access-controlled ledger: date, product ID, source, consent status, requested next step.
5. Validate demand with at least five qualified conversations per market before producing the remaining eight planned titles.
6. Do not call interest a sale. A sale requires a completed payment verified against the processor.

## Phase 1 — checkout and entitlement
After explicit owner approval and once price IDs are configured:
1. Add digital product IDs and fixed prices to Garcar Billing's authoritative catalog.
2. Stripe remains payment processor; Garcar Billing remains the entitlement source of truth.
3. Create Checkout Sessions server-side. Never trust a browser-supplied price or amount.
4. Verify webhook signatures and event idempotency.
5. On confirmed paid event only, create a purchase record and one-time entitlement.
6. Send a time-limited signed download URL or authenticated customer-library link.
7. Record delivery event, timestamp, product version, and download status.
8. Refund/dispute events revoke or suspend entitlement according to the published policy.

## Phase 2 — email automation
- Separate opt-in lists by product market.
- Store consent timestamp, source, disclosure version, and unsubscribe state.
- Require double opt-in where practical.
- Suppress unsubscribed, bounced, and complained addresses.
- Every broadcast needs human approval before release.
- Do not send to scraped, purchased, or guessed addresses.

## Minimal data model
- `products(id, slug, title, market, price_minor, currency, status, version)`
- `orders(id, customer_id, processor_session_id, payment_status, created_at)`
- `order_items(order_id, product_id, unit_amount_minor)`
- `entitlements(id, customer_id, product_id, order_id, status, granted_at, revoked_at)`
- `deliveries(id, entitlement_id, asset_version, delivered_at, download_count)`
- `consents(id, email_hash, market, source, consent_text_version, consented_at, withdrawn_at)`
- `email_events(id, consent_id, campaign_id, event_type, occurred_at)`
- `audit_events(id, event_type, subject_id, payload_hash, occurred_at)`

## Security and reliability requirements
- Keep payment secrets server-side in the existing secret manager; never commit keys.
- Verify webhook signatures, deduplicate by processor event ID, and fail closed on unknown products.
- Store paid assets outside the public static repository.
- Use expiring, unguessable download tokens; do not expose permanent public file URLs.
- Log state transitions without logging card data or raw secrets.
- Provide a clear refund/contact policy before taking payment.
- Back up orders, entitlements, and delivery audit records.

## Release gates
- [ ] Product manuscript approved and proofread.
- [ ] Price, refund policy, terms, privacy notice, and support contact approved.
- [ ] Stripe digital-product Price IDs created by owner.
- [ ] Webhook signature and idempotency tests pass.
- [ ] Paid-only entitlement test passes in test mode.
- [ ] Download access test passes for paid, unpaid, refunded, and expired cases.
- [ ] Email consent, unsubscribe, and suppression tests pass.
- [ ] Owner approves production release.

## Current status
Catalog preview and campaign/architecture documentation are committed separately from the service checkout. Payment, list signup, email sending, and automated fulfillment remain disabled pending the release gates above.
