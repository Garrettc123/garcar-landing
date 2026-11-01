# Garcar Local Operating Console

A zero-dependency, local-first operator console covering working foundation modules across the eight-division Garcar Enterprise portfolio.

## Run

Requires Python 3.10+; no third-party packages.

\`\`\`bash
cd platform
python server.py
\`\`\`

Open http://127.0.0.1:8788 and paste the one-time local admin token printed by the server. The app binds to loopback and stores data in SQLite WAL mode. Keep the token private.

Optional synthetic demonstration records:

\`\`\`bash
python server.py --demo
\`\`\`

Run checks:

\`\`\`bash
python -m py_compile server.py
python -m unittest discover -s tests -v
python smoke_test.py
python ../divisions/validate_catalog.py ../divisions/catalog.json
\`\`\`

Environment:
- GARCAR_PORT: local port (default 8788)
- GARCAR_DB_PATH: alternate SQLite database path
- GARCAR_ADMIN_TOKEN: stable local token; otherwise a random token is generated at startup

## Test coverage

- 29 standard-library unit tests are authored.
- 19 loopback HTTP smoke checks are authored; they use synthetic records and a temporary database.
- GitHub Actions is configured to run Python compile, unit tests, smoke tests, and catalog validation. See the PR status; a GitHub runner has not yet successfully executed those jobs.

## Working local modules

- **Revenue Automation:** business lead CRM, stages, opportunity pipeline, valid-offer link, and lead-response scenario model.
- **Digital Products:** canonical digital catalog visibility; secure checkout and protected delivery are not connected.
- **AI Operations Studio:** document/support workflow work queue; no AI model inference or automatic customer replies.
- **Wealth Forge:** manual inflow/outflow ledger, revenue-quality classification, expense review, runway scenario, and 13-week cash scenario; no bank connection or financial advice.
- **Enterprise Intelligence:** local document register and keyword search with source references; no embeddings, model, or GraphRAG.
- **Industry Solutions:** task/exception queues for dispatch, maintenance, and shift handoffs; no operational equipment control.
- **Infrastructure:** SQLite WAL, diagnostics, local backup inventory, checksum verification, and backup SQLite integrity checks.
- **Governance & Security:** local action approval register and SHA-256 event hash chain; approval decisions do not execute actions.

## API

Public read-only:
- GET /api/health
- GET /api/catalog

All other endpoints require the X-Admin-Token header:
- GET /api/dashboard, /api/leads, /api/opportunities, /api/interviews, /api/approvals
- POST /api/leads, /api/leads/{id}/update
- POST /api/opportunities, /api/opportunities/{id}/update
- POST /api/interviews
- GET /api/finance/entries, /api/finance/summary, /api/finance/quality, /api/finance/expense-review; POST /api/finance/entries, /api/finance/forecast, /api/finance/runway
- GET /api/knowledge/docs, /api/knowledge/search, /api/knowledge/links, /api/knowledge/graph-search; POST /api/knowledge/docs, /api/knowledge/links
- POST /api/documents/extract and /api/support/draft (deterministic, review-only)
- GET /api/work-items; POST /api/work-items, /api/work-items/{id}/update
- GET /api/workflows/definitions, /api/workflows/runs; POST /api/workflows/runs, /api/workflows/runs/{id}/action
- GET /api/system/diagnostics, /api/system/backups; POST /api/system/backup, /api/system/backup/verify
- GET /api/product-readiness; POST /api/product-readiness/{offer_id}/update
- GET /api/approvals; POST /api/approvals, /api/approvals/{id}/decision
- GET /api/audit, /api/audit/verify
- GET /api/simulate/lead-value

## Release limitations

This is a local single-operator foundation, not a production multi-tenant SaaS. It has not been deployed. No Stripe, bank, outbound email/SMS, customer CRM, external API, or cloud infrastructure connection is implemented. No live payment, booking, refund, data export, secret rotation, or production write can execute. Pipeline values are not revenue; scenario outputs are not forecasts. Initial CRM deliberately omits phone/email collection. Use synthetic data for demos.

Production release still requires independent authentication and authorization, tenant isolation, secure hosting, CSRF protections if cookie auth is introduced, encrypted off-site backups, retention/deletion controls, security monitoring, formal migrations, recovery exercises, payment webhook and digital entitlement integrations, and external security review.

## Android / Termux

See [TERMUX_SETUP.md](TERMUX_SETUP.md) for device-local setup, test, and run instructions.

## Security boundary

See [SECURITY_MODEL.md](SECURITY_MODEL.md) for the local threat model, implemented controls, known gaps, and production hardening requirements.
