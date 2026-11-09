# Division 08 — Garcar Governance & Security

## Mission
Define and enforce controls for every division. Governance is a shared control function, not permission for autonomous systems to bypass the owner.

## Product and service catalog
| ID | Capability | State |
|---|---|---|
| GS-001 | Policy and access-control baseline | Specification |
| GS-002 | Evidence and audit ledger | Architecture; implementation needs verification |
| GS-003 | Security and privacy assessment | Planned service |
| GS-004 | Release and change approval workflow | Specification |
| GS-005 | Incident and recovery playbook | Specification |

## Mandatory control lifecycle
Propose → validate → policy-check → owner-approve → authorize → execute → verify → record → monitor → revoke if needed.

Approval is scoped to an exact action, resource, environment, time window, and risk. General planning requests do not authorize external side effects.

## Default-deny rules
No external email, SMS, or customer notification without explicit approval. No live payment, refund, transfer, payout, or billing change without explicit approval. No paid subscription, hosting upgrade, API commitment, or purchase without explicit approval. No production write or destructive operation without approval and rollback plan. No secret disclosure or rotation without approval. No certification, penetration-test, or production-security claim without evidence.

## Evidence model
Record action ID, requesting principal, resource, environment, policy version, approval reference, timestamp, execution result, verification result, artifact hash, and rollback status. Never log raw credentials, card data, or unnecessary personal data.

## Security baseline
Least privilege; strong privileged authentication; secrets outside repositories; input validation/output encoding; dependency review; tenant isolation; tested backups; incident response; human oversight for consequential actions.

## Metrics
Unauthorized-action blocks; policy coverage; stale credentials; vulnerabilities by severity; restore success; audit completeness; response time; exceptions; approval latency.

## Release gates
Threat model and asset inventory; role/permission matrix; default-deny tests; audit integrity verification; incident/recovery exercise; privacy/retention rules; owner approval for production enforcement.

## Status
This defines required controls. It does not prove that all Garcar repositories or deployed services currently enforce them.