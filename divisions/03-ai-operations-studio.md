# Division 03 — Garcar AI Operations Studio

## Mission
Design, implement, and support narrowly scoped AI-assisted workflows for small and medium businesses. Sell measurable process improvements, not generic claims about autonomous AI employees.

## Product catalog
| Offer | Product | Pricing approach | Initial scope |
|---|---|---|---|
| AO-001 | Workflow Discovery & Automation Map | Quote after discovery | Process map, risk register, automation shortlist |
| AO-002 | Document Intake Assistant | Implementation + support | Extract, classify, route documents with human review |
| AO-003 | Customer Support Drafting Assistant | Implementation + support | Draft responses for staff approval |
| AO-004 | Internal Knowledge Assistant | Implementation + support | Search approved internal documents with citations |
| AO-005 | Managed Workflow Reliability | Monthly quote after pilot | Monitoring, incident triage, versioned improvements |

Do not publish pricing until scope, infrastructure cost, data sensitivity, and support burden are known.

## Sales system
Target firms with repeatable administrative work and an accountable process owner. Establish task volume, time per task, error cost, source-system access, data class, exception rate, and approval needs. Demonstrate with synthetic or redacted data. State model limits, human review, and measurable pilot result.

## Technical operating pattern
- Intake: authenticated request and scoped file/data access.
- Orchestration: deterministic workflow with bounded model calls.
- Retrieval: approved knowledge sources only; citations/source IDs required.
- Execution: allow-listed tools; read-only by default.
- Review: human approval for external communications, financial actions, destructive writes, and high-impact decisions.
- Evidence: source reference, model/provider/version, policy result, output, reviewer, tool actions, timestamps, errors.
- Recovery: idempotent retries, exception queue, rollback, operator alert.

## Safety and security
Treat retrieved content as untrusted. Protect secrets and personal data. No customer-data training without documented permission. Models cannot self-grant permissions or change policy. Probabilistic output is not verified fact.

## Metrics
Task completion; human correction; exception rate; latency; cost per task; unsafe-action blocks; source citation coverage; measured time saved; incident rate.

## Release gates
Workflow and owner identified; data permission confirmed; synthetic evaluation set; pre-agreed thresholds; fallback and rollback tested; cost ceiling established; pilot reviewed.

## Status
AI Operations Studio is a product and operating plan. Existing agent repositories require individual inspection and test evidence before customer capability is claimed.