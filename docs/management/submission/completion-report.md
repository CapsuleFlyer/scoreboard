# Test Completion Report — Scoreboard

**Course:** SE3002 – Software Quality Engineering  
**Project period:** 19–29 November 2026  
**Submission date:** 29 November 2026  
**Evidence current through:** 27 November 2026  
**Team:** Shaheer Sohail (24I-3060), Abubakr Qureshi (24I-3016)

## 1. Executive summary

The available testing evidence shows that the automated test suite completed with 565 passed, 41 expected failures (XFAIL) and 0 unexpected failures. The formal k6 registration tests met the agreed performance thresholds in all four runs, with successful database read-back checks. The production dependency audit found no known vulnerabilities, and `pip check` found no broken requirements.

Outstanding quality risks remain: 12 axe accessibility findings, 22 open SonarCloud vulnerabilities and 40 open bugs, an incomplete ZAP passive scan, and the API database-outage JSON test remains an expected failure (DR-22).

## 2. Test execution summary

| Activity | Result | Assessment |
|---|---|---|
| Full pytest suite | 565 passed, 41 xfailed, 0 failed | Passed with documented expected failures |
| Recovery tests | Registration and admin confirmation recovery passed | Partial; API outage JSON test is XFAIL |
| k6 performance | Four formal runs; all p95 < 500 ms and failures 0.00% | Passed in local test environment |
| Registration database read-back | Match in all four k6 runs | Passed |
| Production dependency audit | No known vulnerabilities in `requirements.txt` | Passed for production requirements |
| `pip check` | No broken requirements | Passed |
| Accessibility axe comparison | 12 before, 12 after; 0 resolved | Findings remain |
| Lighthouse accessibility | Register form 80→86; admin registrations 76→76 | Mixed improvement |
| SonarCloud | 40 open bugs, 22 open vulnerabilities | Requires triage |
| ZAP passive scan | Not completed | Not tested; no pass claim |

## 3. Performance results

Configuration: 1 and 5 virtual users, two runs each, 10-second warm-up and 60-second measurement. Agreed limits: p95 < 500 ms and unexpected failures < 1%.

| Users | Run | p95 (ms) | Requests/s | Failed (%) | Registered | Read-back |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 24 | 78.1 | 0.00 | 5727 | Match |
| 1 | 2 | 26 | 42.3 | 0.00 | 2993 | Match |
| 5 | 1 | 242 | 37.9 | 0.00 | 2679 | Match |
| 5 | 2 | 235 | 37.2 | 0.00 | 2642 | Match |

All four runs met the thresholds. The 5-VU runs showed higher latency and lower throughput. The harness uses a local test server and SQLite; results must not be represented as production capacity.

## 4. Outstanding defects and risks

1. **DR-22:** API database-outage response returns an HTML 500 page rather than the expected JSON error. The relevant test is XFAIL.
2. **Accessibility:** 12 axe findings remained after the after-scan. Review and prioritise them, particularly keyboard and form-label issues where applicable.
3. **SonarCloud:** 40 open bugs and 22 open vulnerabilities remain in the current snapshot. Triage severity, affected code and exploitability; do not assume all findings are equally release-blocking.
4. **Dynamic security testing:** ZAP passive scan was not completed, so dynamic scan coverage is incomplete.
5. **Development dependency audit:** The production requirements audit passed. The separate development requirements audit did not produce a conclusive clean result because its resolver could not resolve the dependency set; do not claim it passed.
6. **Management records:** Actual hours per member and per-week execution metrics were not provided. Update them from the team's work log if available.

## 5. Release-or-hold decision

**Recommendation: HOLD for an unconditional release.**

The automated suite and performance checks are positive, but the evidence is not sufficient for an unconditional release/security sign-off. This recommendation is based on the incomplete ZAP scan, open SonarCloud vulnerabilities, remaining accessibility findings and the known DR-22 API error-contract failure.

### Conditions to reconsider release

- Triage the 22 open SonarCloud vulnerabilities and document disposition/owners for high-priority findings.
- Complete the ZAP passive scan and review its alerts.
- Fix DR-22 or obtain explicit, documented risk acceptance from the project owner.
- Review and prioritise the 12 remaining axe findings; document accepted exceptions.
- Verify defect-log statuses against current GitHub issues.
- Record actual team hours and complete peer review of this report.

A release decision may be changed to conditional release only after the team reviews these items and records who accepted any remaining risks. This report does not claim that the listed conditions have already been met.

## 6. Evidence locations

- Performance: `docs/evidence/performance/`
- Accessibility: `docs/evidence/accessibility/`
- Lighthouse: `docs/evidence/lighthouse/`
- SonarCloud: `docs/evidence/sonar/`
- Recovery tests: `tests/team/test_recovery.py`
- Performance scripts: `scripts/perf_register.js`, `scripts/perf_server.py`, `scripts/run_perf.py`
- Test-management package: `docs/management/submission/`

## 7. Approval

| Role | Name | Decision / signature | Date |
|---|---|---|---|
| Team member | Shaheer Sohail | Pending review | |
| Team member | Abubakr Qureshi | Pending review | |
| Project/instructor approval (if required) | | | |
