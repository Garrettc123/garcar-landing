# Garcar Commercial Launch Gate — 2026-11-15

Status: **PREVIEW ONLY / REVIEW REQUIRED**. This branch changes the existing `index.html`; it does not create another storefront.

## Source-of-truth offer
- **Primary:** $497 Lead Follow-Up Review — one buyer-authorized CRM lead export, agreed response threshold, prioritized callback CSV, evidence-based reason codes, written findings. Target 48 hours **after** validated intake and scope confirmation; timing confirmed per client.
- **Secondary:** $2,500 Callback Clock installation — field mapping, configured threshold rules, repeatable report, handoff, and acceptance review, with documented prerequisites.
- **Quote-required:** two-week custom lead automation (`$3,000` reference price); enterprise AI integration (`$10,000` budget starting reference). Written SOW and access controls before work.
- Live Stripe links checked in prior inventory: review `https://buy.stripe.com/8x2eVddjf0hQ86Tf0f43S2h`; install `https://buy.stripe.com/14AdR95QN3u2af14lB43S2j`. Active link does NOT prove delivered purchases or functioning webhook.

## Evidence and known blockers
- The previous public homepage advertised a `$299` ten-day audit, inconsistent with the active $497 Shopify offering. This PR proposes a **replacement** rather than a second public homepage.
- Live Stripe account inspection (Nov 15) saw 13 PaymentIntents with no successes and 4 failed charges; there are no confirmed sales from that evidence.
- `garcar-emergency-payments` workflow run `43757268709` concluded **failure**. Unable to retrieve usable job logs from GitHub during this inspection.
- Shopify connected store is on a trial. **Do not use Shopify checkout** until plan, payment flow, files and order handling are verified.
- Existing Shopify service listings lack product media. No testimonials or performance numbers should be fabricated.

## Blockers to resolve **before merge or paid promotion**
1. Validate Stripe *test-mode* Checkout or payment links through a signed webhook, durable storage, deduplicated intake, and manual/automated fulfillment notification. Do not run live test charges.
2. Confirm that the $497 and $2,500 links are routed to the correct SKUs, that paid orders reach a monitored system, and that a human can fulfill an order even when automation is down.
3. Ensure there is a secure data-intake process, retention/deletion policy, current Terms/Privacy/Support details, and a buyer contact channel.
4. Produce a real, owner-authorized, privacy-safe callback output from an actual export and inspect all timestamp/timezone fields. No fictional screenshot.
5. Review the page copy, prices, accessibility, mobile layout and outbound scope. Owner authorizes the final merge/publish separately.

## Operator-owned sales sequence
1. Identify a legitimate buyer who owns recent lead data.
2. Draft a specific reason for a review; obtain approval before outbound.
3. Qualify data access and response-window definition. Never request customer personal data through the public inquiry form.
4. Confirm price and scope; buyer chooses checkout; independently verify **paid** state.
5. Run analysis, manually QA reason codes and transfer files securely.
6. Confirm receipt; record actual buyer response in CRM.
7. Offer $2,500 installation only when review confirms a repeatable operational need.

## Definition of success
One new customer has **verified paid payment**, **confirmed data authorization**, **documented delivery and acceptance**, and a **source-linked CRM record**. Repository counts and active payment links do not count as sales.

## Review control
Do not merge this pull request or run paid traffic without explicit owner approval and the launch gates above. No automatic cold outreach, charging, or production mutation has been authorized in this branch.
