# Garcar Enterprise — Shared Control Plane Specification

## Objective
Provide common identity, policy, evidence, finance, and monitoring contracts without forcing all divisions into one monolithic runtime.

## Logical components
1. Identity/access: authenticated principal, role, tenant, division, resource scope.
2. Catalog registry: canonical division and offer identifiers; versioned metadata.
3. Policy engine: default-deny evaluation, risk tier, environment restrictions.
4. Approval service: owner approval bound to exact action, target, scope, expiry.
5. Execution gateway: allow-listed tools/APIs, idempotency, timeouts, bounded retries.
6. Evidence ledger: append-only action records, integrity checks, artifact references.
7. Finance reconciliation: processor events, invoices, refunds, fees, payout state.
8. Observability: health, errors, latency, usage, cost.
9. Incident/recovery: disable switches, credential revocation, rollback, backup restore.

## Action contract
Each proposed action includes action_id, requesting_principal, division_id, action_type, resource, environment, data_classification, expected_side_effects, estimated_cost, idempotency_key, rollback_plan, and approval_required.

Policy result: allow, deny, or require_approval. Missing context, unknown action, expired approval, policy failure, or unverifiable identity must fail closed.

## Risk tiers
- R0 read-only: inspect authorized data.
- R1 local reversible: create local artifacts/test fixtures.
- R2 external reversible: modify remote draft or sandbox resource; approval required.
- R3 external consequential: send messages, charge money, change billing, deploy production, modify customer data; explicit action-specific approval required.
- R4 destructive/high impact: delete data, transfer funds, rotate critical secrets, irreversible migration; separate confirmation and recovery evidence required.

## Canonical events
proposal.created; policy.evaluated; approval.granted; approval.denied; action.started; action.completed; action.failed; verification.passed; verification.failed; payment.confirmed; refund.confirmed; payout.confirmed; incident.opened; access.revoked.

Events include schema_version, event_id, occurred_at, actor_id, division_id, resource_id, correlation_id, evidence_ref. Never store secrets or raw card data.

## Revenue truth
Accept a payment event only after processor signature verification and idempotency checks. Product/order identity, currency, amount, and payment status must match the server-side catalog. Refunds/disputes update entitlement and reporting. Bank payout is a separate state from successful payment.

## Security/reliability
Deny by default; least privilege; short-lived credentials where supported; separate sandbox and production; idempotent retries; no secrets in source/logs; defined evidence retention; tested backup/rollback; cost monitoring.

## Build order
Document schemas and action classes; implement local deterministic policy evaluator; use local storage for tests; test allow/deny/expired approval/missing identity/policy outage; add sandbox adapters only after approval; production providers only after explicit approval.

## Status
Target architecture only. No claim that every component is deployed or that existing Garcar systems comply.