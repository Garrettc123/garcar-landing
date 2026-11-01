# Synthetic Example — Lead Response Audit

**This is fictional sample data for format demonstration only. It is not a real customer, measured result, or case study.**

## Engagement
- Business: DEMO — North Star HVAC
- Review period: fictional 30-day sample
- Evidence: generated synthetic event table
- Prepared by: Garcar demonstration environment

## 1. Executive finding
In this synthetic dataset, lead ownership is not assigned consistently after hours. The exercise demonstrates how the report identifies a process gap, labels assumptions, and converts the finding into a testable pilot.

## 2. Synthetic baseline

| Metric | Synthetic value | Source | Confidence |
|---|---:|---|---|
| Inbound leads | 100 | Generated test fixture | High for fixture only |
| Median first-response time | 42 minutes | Generated event timestamps | High for fixture only |
| Leads with no recorded contact | 20 | Generated test fixture | High for fixture only |
| Duplicate entries | 4 | Generated duplicate IDs | High for fixture only |
| Booking rate | 30% | Supplied assumption | Assumption only |

These numbers must never be attributed to an actual HVAC contractor.

## 3. Illustrative findings

### Finding 1 — After-hours ownership
- Observation: sample leads arriving outside the fictional business-hours window had no assigned owner.
- Evidence: synthetic fixture rows marked `after_hours=true`.
- Impact hypothesis: an unowned lead can remain unworked until the next business day.
- Confidence: high within the generated fixture; no real-world inference.
- Limitation: no actual customer records reviewed.

### Finding 2 — Duplicate lead records
- Observation: four generated records share a synthetic source event identifier.
- Evidence: fixture IDs DEMO-014, DEMO-031, DEMO-058, and DEMO-077.
- Impact hypothesis: duplicates can distort pipeline reports and create repeated follow-up work.
- Confidence: high within the generated fixture.
- Limitation: real integration behavior is not tested.

### Finding 3 — Missing next-step field
- Observation: a portion of the generated records lack a next action.
- Evidence: generated status table.
- Impact hypothesis: missing ownership and next action make follow-up inconsistent.
- Confidence: high within the generated fixture.
- Limitation: no customer staff interviews completed.

## 4. Recommendations
1. Add a named after-hours lead owner and backup.
2. Add source-event deduplication before creating a new lead task.
3. Require an owner and next step for qualified leads.
4. Review the exception queue daily.

## 5. Synthetic pilot acceptance tests
- Valid lead creates one assigned work item.
- Replayed source event does not create a duplicate.
- Lead with no owner enters the exception queue.
- Failed processing is visible and can be retried safely.
- Operator can pause the workflow and use a manual fallback.
- Event report reconciles to all generated fixture rows.

## 6. Commercial status
No customer contract, implementation, invoice, payment, or revenue exists for this synthetic example. The $497 audit and $2,500 installation amounts shown in Garcar materials are proposed price hypotheses only.

## 7. Disclaimer
All company names, timestamps, metrics, and event IDs in this sample are fabricated for demonstration. They are not customer evidence, a case study, forecast, or proof of performance.
