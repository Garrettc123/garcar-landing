# garcar-landing

Public conversion page for Garcar Enterprise roofing and home-services offers.

## Current Revenue Flow

1. Visitor lands on `index.html`.
2. Buyer opens `checkout.html`.
3. `checkout.html` calls `garcar-payments` at `/create-checkout-session`.
4. `garcar-payments` creates the Stripe Checkout session.
5. Stripe redirects the buyer to hosted checkout.
6. Stripe sends billing events to `/stripe-webhook`.
7. Billing events are persisted for onboarding, fulfillment, and revenue reporting.

## Checkout URL

Default API base:

```text
https://garcar-payments.up.railway.app
```

Testing override:

```text
/checkout.html?api=http://localhost:8000
```

## Sellable Offer Keys

| Key | Offer | Payment mode |
|-----|-------|--------------|
| `audit` | Operational Audit | one-time payment |
| `dealdesk` | AI Deal Desk Setup | one-time payment |
| `starter` | Starter Automation | subscription |
| `pro` | Pro Automation | subscription |
| `agency` | Agency Automation | subscription |

## Required Next Step

Replace the mailto buttons in `index.html` with links to:

```html
<a href="/checkout.html?plan=audit">Book Your $197 Audit</a>
```

The checkout page is already connected to the payment API contract. The only remaining production dependency is setting the actual Stripe Price IDs and Railway environment variables in `garcar-payments`.
