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
python -m py_compile server.py digital_delivery.py
python -m unittest discover -s tests -v
python smoke_test.py
python ../divisions/validate_catalog.py ../divisions/catalog.json
\`\`\`

Environment:
- GARCAR_PORT: local port (default 8788)
- GARCAR_DB_PATH: alternate SQLite database path
- GARCAR_ADMIN_TOKEN: stable local token; otherwise a random token is generated at startup

## Test coverage

- 41 standard-library unit tests are authored.
- 23 loopback HTTP smoke checks are authored; they use synthetic records and a temporary database.
- GitHub Actions is configured to run Python compile, unit tests, smoke tests, and catalog validation. See the PR status; a GitHub runner has not yet successfully executed those jobs.

## Working local modules

- **Revenue Automation:** business lead CRM, stages, opportunity pipeline, valid-offer link, and lead-response scenario model.
- **Digital Products:** canonical 12-product catalog, preview pages, and an isolated test-mode checkout/entitlement service with signed synthetic events, idempotency, expiring limited-use download tokens, and refund revocation. It does not connect to Stripe or take payments.
- **AI Operations Studio:** document/support workflow work queue; no AI model inference or automatic customer replies.
- **Wealth Forge:** manual inflow/outflow ledger, revenue-quality classification, expense review, runway scenario, and 13-week cash scenario; no bank connection or financial advice.
- **Enterprise Intelligence:** local document register and keyword search with source references; no embeddings, model, or GraphRAG.
- **Industry Solutions:** task/exception queues for dispatch, maintenance, and shift handoffs; no operational equipment control.
- **Infrastructure:** SQLite WAL, diagnostics, local backup inventory, checksum verification, and backup SQLite integrity checks.
- **Governance & Security:** local action approval register and SHA-256 event hash chain; approval decisions do not execute actions.


### Digital delivery sandbox

- Create a synthetic pending order with a server-fixed catalog amount.
- Simulate a signed test-mode payment event bound to that order's test checkout reference.
- Grant one entitlement only after the signed event passes signature, mode, product, currency, and amount checks.
- Generate a hashed, expiring download token; raw token is returned only on the successful local test call.
- Serve only fixed product-ID-to-filename PDF assets from the ignored private asset directory.
- Limit each token to three downloads and 30 minutes; simulate a refund to revoke the entitlement and every associated token.
- No Stripe SDK, real payment endpoint, card form, customer email, live webhook, or actual money movement is present.

For local download testing, place the reviewed 12-PDF archive contents in `platform/private_assets/`. Both `private_assets/` and `private_state/` are git-ignored. The local secret files are created with restrictive file permissions where supported.

## Digital delivery sandbox

The local digital sandbox creates synthetic pending orders at server-side catalog prices. A locally HMAC-signed test event grants an entitlement only after test-mode, non-live, order-reference, product, currency, and amount checks pass. A 30-minute download token permits up to three downloads from a fixed product-ID-to-filename allow-list under the ignored `private_assets/` folder. A synthetic refund revokes entitlement and token access.

This is not Stripe integration or a live checkout. No payment, customer purchase, email receipt, or revenue is created. See [TEST_MODE_DELIVERY.md](../digital-products/TEST_MODE_DELIVERY.md).

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
- GET /api/digital/catalog, /api/digital/health, /api/digital/orders, /api/digital/entitlements; POST /api/digital/test-checkout, /api/digital/test-payment, /api/digital/test-refund
- GET /digital/download/{token} (short-lived bearer token; private asset only)
- GET /api/digital/catalog, /api/digital/health, /api/digital/orders, /api/digital/entitlements; POST /api/digital/test-checkout, /api/digital/test-payment, /api/digital/test-refund
- GET /digital/download/{token} (short-lived bearer token; private asset only)
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

This is a local single-operator foundation, not a production multi-tenant SaaS. It has not been deployed. No Stripe, bank, outbound email/SMS, customer CRM, external API, or cloud infrastructure connection is implemented. No live payment, booking, refund, data export, secret rotation, or production write can execute. Pipeline values are not revenue; scenario outputs are not forecasts. Initial CRM deliberately omits phone/email collection. Use synthetic data for demos. Place approved PDF assets in the ignored `private_assets/` directory only after local review. Place the approved PDF assets in the ignored `private_assets/` directory only after local review.

Production release still requires independent authentication and authorization, tenant isolation, secure hosting, CSRF protections if cookie auth is introduced, encrypted off-site backups, retention/deletion controls, security monitoring, formal migrations, recovery exercises, payment webhook and digital entitlement integrations, and external security review.

## Android / Termux

See [TERMUX_SETUP.md](TERMUX_SETUP.md) for device-local setup, test, and run instructions.

## CI runner troubleshooting

See [CI_TROUBLESHOOTING.md](CI_TROUBLESHOOTING.md) for the latest runner ID, job ID, diagnostics, and Termux local verification path.

## Security boundary

See [SECURITY_MODEL.md](SECURITY_MODEL.md) for the local threat model, implemented controls, known gaps, and production hardening requirements.


## Independent local CI runner

Run the independent Garcar build pipeline:

```bash
bash run_garcar_ci.sh
```

It executes compile, unit tests, loopback HTTP smoke tests, and catalog validation in order. It stops on the first failure, writes per-stage logs, a JSON report, and a SHA-256 manifest under `.garcar-builds/`, and returns a non-zero exit code unless every stage passes. Build subprocesses receive a minimal environment rather than inherited API keys or service credentials.

This pipeline does not require a GitHub-hosted runner. It does not deploy, access customer systems, send messages, or process payments. A successful run verifies only the exact local checkout; it is not production approval. The simpler `run_checks.sh` remains available.


## Release evidence gate (review only)

After a successful local CI run, validate its evidence:

```bash
python release_gate.py .garcar-builds/<BUILD_ID>/report.json
```

The gate verifies that all four required stages passed, referenced logs exist and match their SHA-256 values, the manifest matches the report and logs, and external actions were disabled. It fails closed if evidence is missing or inconsistent. A valid result means the build evidence is ready for human release review only; it does not merge the PR, deploy software, or authorize customer-facing use.
