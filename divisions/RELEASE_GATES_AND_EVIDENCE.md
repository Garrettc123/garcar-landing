# Release Gates and Evidence Register

## Evidence register template
| Field | Required value |
|---|---|
| Product ID and version | Stable catalog ID + version |
| Source revision | Commit SHA |
| Environment | local / test / sandbox / production |
| Test evidence | Command, date, result, artifact |
| Security evidence | Threat model, auth tests, scan results |
| Data approval | Owner, scope, retention |
| External-action approval | Exact action, target, expiry |
| Deployment evidence | Provider/resource, deployment ID, health check |
| Finance evidence | Processor event, reconciliation reference |
| Limitations | Known gaps and risks |
| Release decision | Approved / rejected / deferred, approver and date |

## Gate A — Specification
Buyer, problem, workflow, non-goals, acceptance criteria, data classes, cost hypothesis, and owner documented.

## Gate B — Local implementation
Code committed; tests runnable offline; synthetic fixtures; no secrets; no external side effects by default.

## Gate C — Sandbox
Separate test credentials; signed webhook tests; replay/idempotency; entitlement/refund tests; failure-path tests; owner approval before connecting a sandbox account.

## Gate D — Production
Written owner approval; lawful customer/data permission; approved budget; security review; rollback; support; live monitoring; finance reconciliation.

## Evidence language
- Created: artifact exists.
- Tested: named test ran and passed.
- Verified: independent check confirms expected state.
- Deployed: provider reports a deployment.
- Production-ready: all required release gates passed for the stated scope.
- Revenue: successful live payment confirmed by processor; cash received requires payout reconciliation.
