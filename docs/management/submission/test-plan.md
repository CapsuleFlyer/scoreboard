# Test Plan — Scoreboard

**Course:** SE3002 – Software Quality Engineering  
**Project period:** 19–29 November 2026  
**Submission:** 29 November 2026  
**Team:** Shaheer Sohail (24I-3060), Abubakr Qureshi (24I-3016)

## 1. Purpose

This plan defines how the Scoreboard application is evaluated for functional correctness, reliability, performance, accessibility, security and release readiness. It identifies the evidence needed for the final release-or-hold decision.

## 2. Test objectives

1. Verify core tournament and registration workflows.
2. Verify important business rules and error handling.
3. Check recovery behaviour after database interruption.
4. Measure registration performance under controlled load.
5. Check accessibility and record before/after results.
6. Audit production Python dependencies for known vulnerabilities.
7. Group static-analysis findings by rule and file and compare aggregate counts with the baseline.
8. Maintain traceability from quality objectives to tests, results and defects.

## 3. Scope

### In scope

- Registration and tournament business logic.
- API registration and validation endpoints.
- Admin confirmation behaviour.
- Database outage/recovery behaviour.
- Automated unit, integration and end-to-end tests available in the repository.
- k6 registration performance tests.
- Accessibility scans and Lighthouse measurements.
- SonarCloud issue grouping and baseline comparison.
- Production dependency audit using `pip-audit`.

### Out of scope or limitations

- A completed OWASP ZAP passive scan is not available; record it as not run, not passed.
- The k6 environment is a local test server using SQLite, not a production-capacity benchmark.
- Production infrastructure, database scaling and real-world network conditions are not represented.
- SonarCloud findings require triage; their presence alone does not prove exploitability.

## 4. Test approach

| Test level/type | Approach | Evidence |
|---|---|---|
| Unit/business logic | Execute targeted pytest tests and inspect coverage | pytest output and coverage evidence |
| Integration | Exercise API, database and application interactions | pytest integration tests |
| End-to-end | Run configured E2E suite | E2E test output |
| Recovery | Interrupt database availability, restore it and verify subsequent operations | `tests/team/test_recovery.py` |
| Performance | k6 with 1 and 5 VUs, two repetitions each; 10 s warm-up and 60 s measurement | `docs/evidence/performance/summary-*.json` |
| Accessibility | Compare axe and Lighthouse before/after scans | `docs/evidence/accessibility/`, `docs/evidence/lighthouse/` |
| Static analysis | Group SonarCloud bugs and vulnerabilities by rule/file; compare aggregate counts | `docs/evidence/sonar/` |
| Dependency security | Run `python -m pip_audit -r requirements.txt` and `python -m pip check` | terminal evidence/security testing record |

## 5. Environment and tools

- Windows development environment and PowerShell.
- Python 3.12.10.
- pytest for automated tests.
- k6 2.4.0 for load generation.
- Local Flask test server and SQLite database for the performance harness.
- SonarCloud for static analysis.
- axe and Lighthouse for accessibility checks.
- pip-audit for Python dependency auditing.
- GitHub for source control and shared evidence.

Record exact tool versions and environment changes in the relevant evidence files when available.

## 6. Team and responsibilities

| Member | Student ID | Weekly availability |
|---|---|---:|
| Shaheer Sohail | 24I-3060 | 10 hours |
| Abubakr Qureshi | 24I-3016 | 8 hours |
| **Total** | | **18 hours** |

Both members share responsibility for reviewing test evidence and the final submission. Individual task ownership and actual hours must be filled from the team's work log; this plan does not assume an unconfirmed division of work.

## 7. Entry criteria

- Application can be installed and started in the test environment.
- Required test dependencies are installed.
- Relevant test data and configuration are available.
- Test cases and expected outcomes are documented.
- The target branch contains the changes being evaluated.

## 8. Exit criteria

- Required automated test suites have been executed and results recorded.
- Performance runs have been compared with the agreed limits: p95 < 500 ms and unexpected failures < 1%.
- Read-back counts match successful registrations for each formal performance run.
- Accessibility findings and before/after measurements are documented.
- Production dependency audit and `pip check` results are recorded.
- Known failures, XFAILs, open findings and unrun scans are disclosed.
- The completion report contains an explicit release-or-hold decision and rationale.

A test run is not considered passed merely because a command completed. Expected failures, skipped tests, incomplete scans and unresolved findings remain visible.

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Limited project duration | Incomplete testing or documentation | Prioritise core workflows, critical risks and evidence capture |
| Local SQLite/performance harness differs from production | Results may not generalise | State environment limitations; avoid production-capacity claims |
| Open SonarCloud findings | Potential code/security quality risks | Triage severity, affected code and exploitability |
| ZAP scan not completed | Dynamic security coverage incomplete | Record as a limitation; complete scan before security sign-off |
| API outage response mismatch (DR-22) | API clients may receive HTML instead of JSON | Fix or formally accept risk with a documented owner |
| Actual hours and weekly metrics not captured | Management reports may be incomplete | Reconstruct only from reliable logs; otherwise mark unavailable |

## 10. Deliverables

The test plan, three-point estimates, traceability matrix, weekly GQM reports, root-cause analyses, Pareto analysis, test evidence and completion report are maintained under `docs/management/` and `docs/evidence/`.
