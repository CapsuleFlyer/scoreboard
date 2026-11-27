# SonarCloud Issue Analysis

## Baseline

- Baseline commit: f9a73d03d942d1eb27a4193930b6c3322ee9a4c9

- Baseline date: 2026-11-20 11:41

- Project: CapsuleFlyer/scoreboard

## Current findings

Source: SonarCloud Issues API, branch main.

| Issue type | Open | Fixed |
|---|---:|---:|
| Bugs | 40 | 5 |
| Vulnerabilities | 22 | 2 |

## Baseline comparison

| Metric | Baseline | Current open | Difference |
|---|---:|---:|---:|
| Bugs | 45 | 40 | -5 |
| Vulnerabilities | 12 | 22 | 10 |

A negative difference indicates fewer current open findings than the baseline. A positive difference indicates more.

## Grouped findings

The accompanying CSV files contain the current open bugs and vulnerabilities grouped by rule and by file.

- sonar-issues-by-rule.csv
- sonar-issues-by-file.csv

## Limitations

The saved baseline contains project-level measures, commit and date, but no individual issue snapshot. Therefore, this report compares aggregate baseline metrics with current open issue counts. It cannot establish which individual findings are newly introduced, resolved, or unchanged.

The current API export includes open and fixed issues. Only OPEN findings are included in the grouped CSV reports. Fixed counts are reported separately.

Code smells are excluded from the bug and vulnerability breakdown.
