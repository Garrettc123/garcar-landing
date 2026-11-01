# Garcar Enterprise — Shared Product Delivery Blueprint

## Product layers
1. Experience: accessible web UI, forms, reports, download/print, responsive layout.
2. Domain: division-specific rules and calculations; deterministic where possible.
3. Workflow: explicit state machine, bounded retries, idempotency, human approval gates.
4. Data: tenant-scoped records, data minimization, retention and deletion.
5. Integration: allow-listed connectors behind adapters; sandbox first.
6. Governance: identity, policy, approval, evidence, revocation.
7. Operations: health, logs, metrics, backup, recovery, cost controls.

## Standard repository layout
```
products/
  <division>/
    <product-id>/
      README.md
      app/
      tests/
      fixtures/
      docs/
      config.example.json
```
Never commit live credentials. Example configuration contains variable names and safe sample values only.

## Shared product API conventions
- Health: GET /health (no secrets or internal topology in response).
- Version: GET /version (build/commit identifier).
- Readiness: GET /ready (dependencies checked with bounded timeout).
- Mutations require authenticated principal, authorization, validation, idempotency where applicable, and audit event.
- External actions default to disabled until a separate owner approval is provided.
- Errors are structured and do not expose secrets or stack traces to end users.

## Standard test gates
- Unit tests for domain logic and calculations.
- Contract tests for API boundaries and event schemas.
- Authorization tests for every protected resource.
- Negative tests: missing identity, insufficient scope, expired approval, invalid input, duplicate event, timeout, dependency outage.
- Privacy tests: sensitive data redaction and tenant separation.
- Recovery tests: restart, retry, rollback, restore.
- Accessibility and responsive UI review.
- Cost ceiling and provider quota recorded before hosted deployment.

## Digital commerce contract
Digital products and service products have separate offer IDs, checkout configuration, entitlement rules, and delivery permissions. Never reuse a service payment link for a digital product. Verify processor webhook signature, event idempotency, exact product/price/currency match, and paid status before granting access. Handle refunds/disputes and revoke or review entitlements according to published terms. Paid files must not be stored in a public static repository.

## Data handling
Use synthetic data for demos. Collect minimum necessary data. Customer records require written permission, purpose limitation, retention period, deletion path, and access review. No model training on customer data without documented permission.

## Release states
idea → specified → built-local → tested-local → sandbox-verified → approved-for-production → deployed-and-verified → monitored.
State changes require evidence. “Deployed” without health checks is not “deployed-and-verified”.

## Operational handoff
Every product must include owner, support channel, support hours, severity matrix, known limitations, dependency inventory, backup/restore or export plan, and rollback/disable switch.
