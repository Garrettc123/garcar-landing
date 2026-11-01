# Garcar Local Platform — Threat Model and Security Boundary

## Intended use
A single local operator using a loopback-bound development console with synthetic or low-sensitivity business records. It is not approved for public hosting, regulated information, customer production data, or payment information.

## Assets
- Local SQLite database and backup files
- Local operator token printed at startup
- Product catalog and local documents
- Lead, opportunity, finance, work-item, approval, and audit records
- Product release-state and evidence references

## Trust boundaries
1. Browser tab to local HTTP service: one local bearer token is sent in the `X-Admin-Token` header.
2. Service to local SQLite file: read/write access is granted to the operating-system account running the process.
3. Local knowledge store: document text is supplied by the operator; search output is lexical and is not trusted as authoritative without checking its source reference.
4. Approval register: it records requests and decisions but has no execution capability.
5. External environment: there is no network integration for payments, email, SMS, CRM, cloud deployment, or bank data.

## Implemented controls
- HTTP server binds to `127.0.0.1`, not all network interfaces.
- Random high-entropy token is generated if no local token is configured.
- Token is compared using constant-time comparison.
- Authenticated routes require `X-Admin-Token`.
- JSON request body size is capped at 64 KiB.
- Values are validated and length-limited; SQL values are parameterized.
- Table names for list queries are allow-listed.
- Browser renders user-controlled data through HTML escaping.
- SQLite enables WAL, foreign keys, and busy timeout.
- Audit events are linked by SHA-256 hashes and can be checked for modification.
- Local backups are created via SQLite's online backup API.
- No external actions or execution adapters exist.

## Known gaps — do not treat as production security
- One shared local bearer token; no individual identity, password, MFA, RBAC, or tenant separation.
- The token is displayed in the terminal and must be protected by the device/account boundary.
- SQLite database and local backups are not encrypted by this application.
- A privileged operator or filesystem attacker can rewrite the database and recalculate the hash chain; this is not WORM storage.
- No off-site backup, key rotation, central monitoring, incident response integration, or recovery-time guarantee.
- No formal migration runner or schema versioning mechanism.
- No HTTPS; loopback-only transport is the intended boundary.
- No rate limiting or lockout; do not bind the service to a LAN or public interface.
- No independent security audit or penetration test.
- Manual approval records are not production authorization and do not execute work.
- Release board evidence references are user-entered and not independently verified.

## Production hardening required
Before any hosted or customer-facing use:
1. Adopt real user identity, MFA, role-based authorization, session revocation, and tenant isolation.
2. Use HTTPS, secure headers, CSRF protections appropriate to the chosen auth model, rate limits, and abuse monitoring.
3. Move secrets to an approved secret manager; never store tokens in source or browser local storage.
4. Encrypt databases, backups, and sensitive fields; implement retention and verified deletion.
5. Add schema migrations, backup restore drills, off-site encrypted backups, and measured recovery objectives.
6. Add dependency and container scanning, SBOM, signed artifacts, static analysis, and independent security review.
7. Add immutable or externally anchored audit storage with independent verification.
8. Implement explicit per-action approvals in the execution service; use idempotency, scope/time-bound grants, allow-listed actions, and reliable rollback.
9. Validate payment webhooks, product-price mapping, entitlements, refunds, disputes, and signed file delivery before digital commerce.
10. Complete synthetic, sandbox, and customer acceptance testing and obtain written release approval.

## Safe operator rule
Keep the platform bound to loopback, use synthetic data, protect the token and device, keep backups private, and stop the server when not in use. Do not enter bank credentials, card data, passwords, medical details, or sensitive customer records.
