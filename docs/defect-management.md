# Defect Management

Defects are logged as GitHub Issues using the "Defect" template (`.github/ISSUE_TEMPLATE/defect.md`). This page defines the scales, labels and lifecycle used in the report, the Pareto chart and the GQM metrics.

## Severity (impact on users or data)
| Level | Meaning |
|---|---|
| critical | Data loss, security compromise, or the core workflow cannot be used at all |
| major | A workflow gives wrong results or fails, and there is a workaround or limited reach |
| minor | Edge case, inconsistent behaviour, or a rule broken without harm to the workflow |
| trivial | Cosmetic or documentation only |

## Priority (when to fix it)
| Level | Meaning |
|---|---|
| P1 | Fix before any release decision; blocks other testing |
| P2 | Fix in this project cycle |
| P3 | Fix if time allows, or document and accept |

Severity says how bad it is. Priority says how soon. They can differ, for example a trivial typo on the front page can be P1.

## Labels to create in the repository (Issues > Labels)
- Type: `type:defect`
- Severity: `severity:critical`, `severity:major`, `severity:minor`, `severity:trivial`
- Priority: `priority:P1`, `priority:P2`, `priority:P3`
- Status (lifecycle): `status:new`, `status:confirmed`, `status:in-progress`, `status:fixed`, `status:verified`, `status:reopened`, `status:wontfix`
- Category (Pareto): `cat:validation`, `cat:access-control`, `cat:error-handling`, `cat:state-rules`, `cat:dependency`, `cat:date-time`, `cat:config-docs`, `cat:other`

## Lifecycle
new, then confirmed (reproduced by a test or a run), then in-progress, then fixed (change merged), then verified (the test that failed now passes), then closed. A fixed defect that fails again is `status:reopened`, and the reopen count feeds the reopen-rate metric. A defect we accept without fixing is `status:wontfix` and keeps its triage reason in the issue.

## Metrics used in weekly reports (GQM)
- Defect density = confirmed defects / thousand lines of code in scope.
- Requirements coverage = requirements with at least one passing automated test / total requirements.
- Reopen rate = reopened defects / fixed defects.

## Rules
- Do not mark a defect `confirmed` unless a test or run reproduced it. Defects found only by reading the source stay `status:new` until a test confirms them.
- Link every defect to a requirement and, where possible, a risk in `docs/risk-register.md`.
- Root cause analysis (5 Whys and fishbone) is done for at least two major defects, with a corrective and a preventive action.
