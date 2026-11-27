# Test-management submission package

**Project:** Scoreboard  
**Course:** SE3002 – Software Quality Engineering  
**Project period:** 19–29 November 2026  
**Submission date:** 29 November 2026  
**Evidence current through:** 27 November 2026

## Team capacity

| Member | Student ID | Available hours/week |
|---|---|---:|
| Shaheer Sohail | 24I-3060 | 10 |
| Abubakr Qureshi | 24I-3016 | 8 |
| **Total** | | **18** |

The 10 elapsed days from 19 to 29 November represent approximately 10/7 of a week. The corresponding planning capacity is approximately 25.7 hours (Shaheer 14.3; Abubakr 11.4). This is availability, not actual effort. Actual hours must come from the team's work log.

## Contents

- `test-plan.md` — scope, approach, environment, responsibilities and exit criteria.
- `three-point-estimates.csv` — optimistic, most-likely and pessimistic estimates with PERT calculations.
- `traceability-matrix.csv` — quality objectives mapped to tests, evidence and gaps.
- `weekly-reports/` — GQM-based reports for 19–25 and 26–29 November.
- `root-cause-analysis.md` — 5 Whys and fishbone analyses for DR-03 and DR-14.
- `pareto-analysis.md` and `pareto-sonar-issues.csv` — Pareto snapshot of open SonarCloud bugs and vulnerabilities.
- `completion-report.md` — test summary and release-or-hold recommendation.

## Evidence integrity

- Full automated suite: 565 passed, 41 xfailed, 0 failed.
- Formal k6: 1 and 5 virtual users, two runs each, 10 s warm-up and 60 s measurement. All four runs met p95 < 500 ms and unexpected failures < 1%; read-back matched.
- Production dependency audit: no known vulnerabilities in `requirements.txt`; `pip check` reported no broken requirements.
- Accessibility: axe remained at 12 findings; Lighthouse accessibility scores were 80→86 and 76→76.
- ZAP passive scan was not completed. Do not report it as passed.
- API database-outage test is XFAIL (DR-22: HTML 500 instead of expected JSON error).
- Actual weekly hours, per-week test counts and individual task ownership were not supplied and are not invented.

Before submission, verify defect statuses against GitHub, add actual hours if your work log contains them, review the release decision, and commit this directory.
