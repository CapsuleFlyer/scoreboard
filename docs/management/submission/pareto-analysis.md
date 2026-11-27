# Pareto Analysis — Open SonarCloud Bugs and Vulnerabilities

**Snapshot:** 27 November 2026 project evidence  
**Scope:** Open SonarCloud bugs and vulnerabilities only. Code smells are excluded.  
**Total:** 62 open issues (40 bugs and 22 vulnerabilities).

> This is a Pareto view of SonarCloud rule groups, not a count of independently confirmed product defects. Do not conflate it with the separate `docs/management/defects.csv` defect log.

## Ranked data

| Rank | Type | Rule | Open issues | Cumulative % |
|---:|---|---|---:|---:|
| 1 | BUG | `Web:InputWithoutLabelCheck` | 37 | 59.68% |
| 2 | VULNERABILITY | `Web:S5725` | 6 | 69.35% |
| 3 | VULNERABILITY | `pythonsecurity:S8707` | 5 | 77.42% |
| 4 | VULNERABILITY | `githubactions:S8541` | 4 | 83.87% |
| 5 | VULNERABILITY | `githubactions:S8544` | 4 | 90.32% |
| 6 | BUG | `python:S930` | 2 | 93.55% |
| 7 | VULNERABILITY | `python:S2068` | 1 | 95.16% |
| 8 | VULNERABILITY | `pythonsecurity:S5145` | 1 | 96.77% |
| 9 | VULNERABILITY | `githubactions:S7637` | 1 | 98.39% |
| 10 | BUG | `python:S1763` | 1 | 100.00% |

Detailed values are in `pareto-sonar-issues.csv`. The leading rule, `Web:InputWithoutLabelCheck`, accounts for 37 of the 62 open bugs and vulnerabilities in this snapshot. Prioritise reviewing the affected templates, then triage vulnerability rules by severity and exploitability.

## Interpretation and limitations

- Rule counts show where the scanner reports the largest concentration of findings; they do not prove root cause or exploitability.
- One rule may affect many files, and one file may contain multiple findings.
- The SonarCloud baseline is aggregate-only for this comparison; there is no baseline issue-level snapshot to identify each finding as new, resolved or unchanged.
- Re-export before final submission if the SonarCloud project has changed since this snapshot.
