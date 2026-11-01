# Digital Products — Test-Mode Checkout and Protected Delivery

Checkpoint: 2026-11-01  
Code: `platform/digital_delivery.py`  
UI: Local Operating Console → Digital sandbox

## What is implemented

A local test-only flow now demonstrates the lifecycle from a catalog product to a protected PDF download:

1. An authenticated local operator chooses a digital product ID.
2. The server reads the authoritative price from `digital-products/catalog.json`; it ignores any browser-supplied amount.
3. A synthetic pending order is created with a random test order reference and pseudonymous buyer reference.
4. The operator explicitly runs the local test payment simulator.
5. The server creates a synthetic event, signs it with a local HMAC secret, and runs the same signature-processing path used by the test webhook verifier.
6. The processor checks the signature, test mode, `livemode=false`, event ID format, original checkout reference, product ID, currency, and exact catalog amount.
7. Only a matching success event grants one entitlement.
8. The service returns a random bearer download token. Only its HMAC digest is stored in SQLite.
9. A download is permitted only if the order remains paid, the entitlement remains active, the token is unexpired, the download limit has not been reached, and the mapped private PDF file exists.
10. A synthetic refund marks the order refunded, revokes the entitlement, and revokes every token associated with it.

## Fixed product asset allow-list

The server maps the 12 catalog product IDs to fixed filenames. The caller cannot provide a file path or filename. Files are served only from the local `private_assets/` directory after path resolution verifies the file remains inside that directory.

The folder is git-ignored and is not committed to the public repository. Place the reviewed 12-PDF library in that folder on the machine running the local app.

## Token controls

- 30-minute expiration.
- Maximum three successful downloads.
- HMAC hash stored instead of raw token.
- SHA-256/HMAC constant-time signature comparison.
- Revocation on synthetic refund.
- Bearer tokens are redacted from local HTTP access logs.
- Download responses use attachment disposition and no-store caching headers.

## Endpoints

Authenticated local operator API:
- `GET /api/digital/catalog`
- `GET /api/digital/health`
- `GET /api/digital/orders`
- `GET /api/digital/entitlements`
- `POST /api/digital/test-checkout`
- `POST /api/digital/test-payment`
- `POST /api/digital/test-refund`

Bearer-token file endpoint:
- `GET /digital/download/{token}`

## What is not implemented

- No Stripe SDK or Stripe account connection.
- No real Checkout Session or payment URL.
- No card data collection or charge.
- No production processor webhook endpoint.
- No customer email collection or delivery email.
- No real customer purchase, refund, or revenue.
- No automated subscription, tax, dispute, or refund policy handling.
- No hosted customer library or account system.
- No independent penetration/security audit.

This module is a local simulation to test entitlement and file-access rules. It must not be represented as a live e-commerce system or used to deliver files for real customer payments.

## Next release gate

After the legal, pricing, refund, support, privacy, and asset approvals are complete, a separate owner-authorized implementation must connect the real processor in test mode first, validate its signatures/idempotency contract, and independently verify paid, unpaid, duplicate, expired, refunded, and disputed states. Only a separately authorized release can enable live payments.
