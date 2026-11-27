# Weekly GQM Report — 26 to 29 November 2026

**Project:** Scoreboard  
**Evidence current through:** 27 November 2026  
**Submission:** 29 November 2026  
**Team:** Shaheer Sohail (24I-3060), Abubakr Qureshi (24I-3016)

## Goal

Complete remaining quality checks, capture reproducible evidence and assess release readiness.

## Questions and metrics

| GQM question | Metric | Result |
|---|---|---|
| Did the full automated suite pass? | Passed / failed / xfailed | 565 passed, 0 failed, 41 xfailed |
| Did recovery scenarios work after service restoration? | Recovery tests passed | Registration recovery and admin confirmation recovery passed |
| Did the API outage response meet the expected JSON contract? | API outage test | XFAIL: default HTML 500 instead of JSON error (DR-22) |
| Did performance meet agreed limits? | p95 < 500 ms; unexpected failures < 1% | All 4 runs met both limits |
| Did database read-back match successful registrations? | Read-back delta equals successful registration count | Yes, all 4 runs |
| Were production dependencies free of known audit findings? | pip-audit and pip check | No known vulnerabilities in `requirements.txt`; no broken requirements |
| Did accessibility findings decrease? | axe findings before vs after | 12 before and 12 after; 0 resolved |
| Was dynamic security scanning completed? | ZAP passive scan status | Not completed |

## Formal k6 results

Configuration: 1 and 5 virtual users; two runs per user count; 10-second warm-up; 60-second measured phase.

| Virtual users | Run | p95 (ms) | Requests/s | Unexpected failures | Read-back |
|---:|---:|---:|---:|---:|---|
| 1 | 1 | 24 | 78.1 | 0.00% | Match |
| 1 | 2 | 26 | 42.3 | 0.00% | Match |
| 5 | 1 | 242 | 37.9 | 0.00% | Match |
| 5 | 2 | 235 | 37.2 | 0.00% | Match |

All four runs met p95 < 500 ms and unexpected failures < 1%. The five-user runs had higher latency and lower throughput than the one-user runs. These are local test-environment results, not a production-capacity guarantee.

## Issues and actions

1. DR-22 remains an expected failure and should be fixed or explicitly accepted before release.
2. The ZAP passive scan remains incomplete.
3. Twelve axe findings remain; review and prioritise them.
4. SonarCloud currently reports 40 open bugs and 22 open vulnerabilities. Triage is required; baseline aggregate counts were 45 bugs and 12 vulnerabilities.
5. Actual member hours and week-specific activity totals were not supplied. Enter them from the team's work log if available.

## Assessment

Automated execution and performance checks are positive. However, unresolved accessibility findings, open SonarCloud vulnerabilities and the incomplete ZAP scan prevent an unconditional security/accessibility sign-off.
