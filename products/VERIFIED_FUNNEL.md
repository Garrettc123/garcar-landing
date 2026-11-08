# Garcar verified multi-product funnel (November 7, 2026)

## Live site
- Main service entry: https://garcar-followup-review.vercel.app/
- All products: https://garcar-followup-review.vercel.app/products/
- Vercel production deployment: dpl_3s1S6cuM3iBgzxMH3bpL7j1hLMQo (READY)
- All nine product detail routes have passed external public content fetch.

## Authoritative product mapping
`products/verified-funnel-catalog.json` distinguishes **Stripe price verification** from **fulfillment readiness** and provides the exact Stripe payment-link identifiers. It is a snapshot and must be refreshed from Stripe before creating new buyer-specific offers.

## Funnel rules
1. Source real intent from authenticated CRM/email conversations; don't manufacture a lead.
2. Match exactly one most relevant product and mention its scope accurately.
3. Only $497 Lead Follow-Up Review and $299 AI Automation Audit link to direct checkout. The $299 Stripe product copy is historically contractor-specific; confirm fit with noncontractor buyers before payment.
4. $2,500 installation and both monthly managed services require a written scoped engagement and verified capacity. Do not send their existing checkout URLs before qualification.
5. $27 prompt pack, $79 mini-course, $149 toolkit and $97 Repo Atlas are **preview-only** while full delivery evidence remains missing. Existing legacy Stripe links are not authorization to sell undelivered products.
6. Never count clicks or live checkout availability as revenue: reconcile unique successful Stripe payment intents and the account's available/pending/payout history.
7. Customer data intake needs an agreed secure route and minimum necessary fields. No public upload route exists on this site.
8. The daily recurring `Garcar Daily Multi-Product Revenue Actions` automation has been updated to route prospects by product and prepare reviewed, non-duplicative drafts; it cannot guarantee actual sales.

## Blockers
- Fulfillment/delivery checks for four digital products.
- Demonstrated capacity and support contracts for higher-value managed offerings.
- Stripe negative balance and historical insufficient-funds transfer failures.
- No new verified customer payment from this release.
- This PR is documentation/reference only; the live Vercel site source is currently deployed by API, not Git-connected.
