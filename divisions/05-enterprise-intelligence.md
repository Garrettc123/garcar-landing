# Division 05 — Garcar Enterprise Intelligence

## Mission
Package Garcar knowledge, orchestration, and decision-support architecture for enterprise buyers. Sell controlled, auditable intelligence workflows—not unrestricted autonomous operation.

## Product catalog
| Offer | Product | Commercial model hypothesis | Buyer |
|---|---|---|---|
| EI-001 | Enterprise Knowledge Fabric Assessment | Fixed-fee assessment | CTO / CIO / operations |
| EI-002 | Governed Knowledge Assistant | Implementation + license | Knowledge-intensive teams |
| EI-003 | Workflow Orchestration Layer | Implementation + support | Operations / engineering |
| EI-004 | Evidence & Decision Ledger | License / managed service | Risk / compliance / IT |
| EI-005 | RHNS Architecture Evaluation | Technical assessment after proof | Enterprise technology leaders |

## Architecture boundaries
Knowledge plane: ingestion, metadata, source lineage, access filters, retention. Retrieval plane: hybrid search/graph retrieval with source-level access checks. Reasoning plane: bounded model reasoning with citations and uncertainty disclosure. Orchestration plane: deterministic state transitions and allow-listed tools. Governance plane: policy, owner approval, audit, revocation. Evidence plane: tamper-evident records and verification procedures.

## Sales system
Start with technical discovery and evidence-based architecture review. Ask about source systems, access controls, data residency, audit requirements, latency, availability, and failure modes. Demonstrate with synthetic or approved redacted data. No security certification or compliance claim without independent evidence.

## Operating requirements
Tenant isolation; per-source authorization; encryption in transit and at rest where supported; secret manager; provenance for retrieved claims; human approval for consequential actions; evaluation for retrieval, groundedness, permission leakage, and tool misuse; backup/restore; incident response; model/provider cost ceilings.

## Metrics
Retrieval precision/recall; grounded-answer rate; access leakage tests; workflow completion; operator override; latency; cost/task; availability; incidents.

## Release gates
Threat model; synthetic tenant isolation; permission-leakage tests; evidence-chain verification; load/recovery tests; substantiated security claims; signed paid-pilot scope.

## Status
RHNS, GraphRAG, and multi-agent orchestration appear in prior project context as architecture or partial implementation concepts. This is not proof of an integrated enterprise product, production reliability, certification, or customer deployment.