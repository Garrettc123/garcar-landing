# Garcar Local Operating Console

Zero-dependency local-first console for the eight-division Garcar Enterprise portfolio.

## Run
Requires Python 3.10+; no third-party packages.

\`\`\`bash
cd platform
python server.py
\`\`\`

Open http://127.0.0.1:8788 and paste the local admin token printed in the terminal. The app binds to loopback and stores records in SQLite WAL mode.

For clearly synthetic demo records:
\`\`\`bash
python server.py --demo
\`\`\`

Run tests:
\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

Optional environment:
- GARCAR_PORT (default 8788)
- GARCAR_DB_PATH (alternate SQLite path)
- GARCAR_ADMIN_TOKEN (fixed local token; otherwise random each run)

## Implemented local modules
- Eight-division, 46-offer canonical catalog reader
- Lead CRM and status tracking
- Opportunity pipeline tied to valid offer IDs
- Validation interview log with permission field and data minimization
- Lead-response opportunity scenario model
- Approval request/decision register (record only)
- SHA-256 hash-chained local audit ledger and verification
- Responsive browser console

## API
- GET /api/health and GET /api/catalog are read-only.
- All other endpoints require X-Admin-Token.
- GET /api/dashboard, /api/leads, /api/opportunities, /api/interviews, /api/approvals, /api/audit, /api/audit/verify
- POST /api/leads, /api/leads/{id}/update
- POST /api/opportunities, /api/opportunities/{id}/update
- POST /api/interviews, /api/approvals, /api/approvals/{id}/decision
- GET /api/simulate/lead-value

## Important limits
This is a local single-operator operating tool, not production multi-tenant SaaS. No Stripe, outbound email/SMS, customer CRM, external APIs, deployments, refunds, or secret rotation is connected. Approval decisions do not execute actions. Scenario outputs are not forecasts. Pipeline amounts are not revenue. Initial CRM deliberately omits phone/email collection. Use synthetic data for demos.

Before production use: implement independent user authentication and authorization, tenant isolation, secure deployment, CSRF protections if cookie auth is introduced, encrypted backup and retention controls, formal data deletion, monitoring, recovery tests, payment webhook and entitlement integrations, and external security review.
