# Division 07 — Garcar Infrastructure

## Mission
Provide a reliable, cost-conscious technical foundation for all divisions. Infrastructure serves validated products; it is not a spending mandate.

## Service catalog
| ID | Capability | Objective |
|---|---|---|
| INF-001 | Source control and release records | Reproducible, traceable changes |
| INF-002 | Application runtime | Minimal observable hosting |
| INF-003 | Data persistence | Backups, migrations, access controls |
| INF-004 | Integration gateway | Authenticated allow-listed APIs |
| INF-005 | Secret management | No secrets in source or logs |
| INF-006 | Observability | Health, errors, latency, cost |
| INF-007 | Recovery | Tested backup and restore |

## Zero-cost-first operation
Use local development and synthetic data first. Reuse existing resources only after checking actual limits and account status. No new service, domain, database tier, paid API, or usage-based resource is provisioned without explicit approval. No production migration is part of this plan. Separate test and production credentials. Record provider, plan, quota, owner, data location, retention, and exit path before adoption.

## Release pipeline
Static analysis and dependency review; unit/contract tests; secret scanning; reproducible build; sandbox smoke test; human approval; controlled deployment with rollback; post-deploy health verification.

## Metrics
Build success; test pass rate; deployment frequency; change failure rate; recovery time; availability; backup restore success; cost per customer; secrets detected.

## Release gates
Dependency/config inventory; no committed secrets; reproducible build; tests pass; restore demonstrated; cost/quota ceiling documented; owner authorizes production change.

## Status
Prior project context reports Railway failures/trial constraints and Vercel billing suspension. These historical observations require fresh account-level checks before relying on providers. This plan does not activate or modify infrastructure.