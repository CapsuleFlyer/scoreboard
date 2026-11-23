# Risk Register and Exit Criteria

Project: SE3002 Final Project, Team Registration and Management (scoreboard). Status: DRAFT v1, 2026-11-20.
Scores are proposals for the group to review. Every member must be able to explain why each score was chosen.

## 1. Scales
Risk score = Likelihood (L) x Impact (I), each 1-5.

| Score | L (how likely the problem is to occur or hit a user) | I (damage if it happens) |
|---|---|---|
| 1 | Rare, no sign of it | Cosmetic |
| 2 | Needs unusual set-up | Minor, easy workaround |
| 3 | Plausible in normal use | Feature degraded, data cleanup needed |
| 4 | Likely, or already seen | Workflow blocked, or security weakened |
| 5 | Already confirmed by running the app | Data loss, or full compromise |

Level: **High** = 15-25, **Medium** = 8-14, **Low** = 1-7.

## 2. Product risks (8)
Evidence IDs refer to `docs/test-basis.md`. RUN = executed against the code, READ = read in source only.

| ID | Risk | L | I | Score | Level | Evidence |
|---|---|---|---|---|---|---|
| R1 | Registration deadline causes a crash. Once `registration_deadline` is set, `can_register()` raises TypeError (timezone-aware vs naive datetimes). Public page and both API registration endpoints return 500. | 2 | 4 | 8 | Medium | N1, RUN. L is 2 because no route sets the deadline, so only a database edit triggers it. |
| R2 | Capacity is consumed by unapproved teams. Pending teams count toward `max_teams`, and the public list shows only confirmed teams, so a tournament can be "full" with no visible teams. | 4 | 3 | 12 | Medium | A4 and N4, RUN. |
| R3 | Inconsistent validation across entry points. Public form: names up to 20 characters, case-sensitive duplicates (`Alpha` and `alpha` both accepted). Admin add: truncates team name to 8 and player names to 10, case-insensitive. API: always requires both player names. Data differs depending on how a team was registered. | 5 | 3 | 15 | High | F3 and N2, RUN. |
| R4 | Broken access control on admin registration actions. Anonymous users are redirected (RUN with CSRF off), but registration routes do not check tournament ownership, so any admin can manage any tournament. | 3 | 4 | 12 | Medium | FR6 RUN; ownership gap READ. Anonymous POST with a real CSRF token not yet observed (F6). |
| R5 | Error handling is broken. The 404 handler renders `ui.index`, which does not exist, so every 404 becomes a 500, including confirming a nonexistent team. | 5 | 2 | 10 | Medium | F2, RUN. |
| R6 | Vulnerable dependencies. pip-audit reported 14 unique advisories across Flask 3.0.0, Werkzeug 3.0.1, python-socketio 5.10.0, python-engineio 4.8.1 and python-dotenv 1.0.0. Exploitability in this app has not been assessed. | 4 | 4 | 16 | High | F7, RUN on Linux. Rerun on Windows. |
| R7 | State rules are weak or bypassed. Reject deletes (no rejected state), confirm is accepted twice, check-in works on unconfirmed teams, and admin manual add skips `can_register()` so it works after registration closes or the tournament starts. | 4 | 3 | 12 | Medium | F4 and N3. Confirm RUN, others READ. |
| R8 | The registration API is CSRF-exempt, so forged or scripted requests are possible. No rate limiting was seen in the files read (not exhaustively checked). | 3 | 3 | 9 | Medium | F8, READ. |

## 3. Project risks (2)

| ID | Risk | L | I | Score | Level | Mitigation |
|---|---|---|---|---|---|---|
| P1 | Time and ownership. Many deliverables, three members, areas not yet assigned, and a viva where unexplained work is zeroed. | 4 | 4 | 16 | High | Assign owners per area this week; review each other's work before commit; keep the three-point estimates updated. |
| P2 | Tooling and environment. Windows locally versus Linux in CI; SonarCloud (hosted) may not be accepted in place of SonarQube; Docker and token set-up. | 3 | 3 | 9 | Medium | Ask the TA about SonarCloud; pin tool versions; document set-up in the repo. |

## 4. 5x5 matrix
Rows are likelihood, columns are impact.

| L \ I | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 5 | | R5 | **R3** | | |
| 4 | | | R2, R7 | **R6, P1** | |
| 3 | | | R8, P2 | R4 | |
| 2 | | | | R1 | |
| 1 | | | | | |

## 5. Risk level decides technique and depth

| Level | Depth |
|---|---|
| High (R3, R6, P1) | Full set: EP plus 3-point BVA, decision tables, state transitions, unit tests to 100% branch coverage, mutation testing on the logic, and an end-to-end test. Root cause analysis for confirmed defects. |
| Medium (R1, R2, R4, R5, R7, R8) | EP and BVA on the inputs, decision table or state test where the risk is a rule, one end-to-end happy path plus the main failure path. |
| Low (none yet) | Smoke test only. |

Technique per risk:

| Risk | Techniques |
|---|---|
| R1 | Unit test of `can_register()` with a deadline set; MC/DC on its conditions |
| R2 | BVA on `max_teams` (below, at and above the limit); decision table for pending versus confirmed |
| R3 | EP and BVA on name length, case, player names and email across all three entry points |
| R4 | Access matrix in Playwright: allowed and denied actions per role |
| R5 | API test: nonexistent IDs and URLs |
| R6 | pip-audit results, mapped to the pinned versions |
| R7 | State transition tests: every allowed change, plus at least one disallowed change from each state |
| R8 | API tests with and without a CSRF token; repeated requests |
| P1, P2 | Weekly progress report and control actions |

Baseline coverage of the scoped code is low (Sonar overall 50.7%, `register.py` 15%, `can_register()` never executed by the upstream tests), so every medium and high risk above needs new tests before it counts as covered.

## 6. Exit criteria (proposed, measurable)

| ID | Criterion | Type | Tied to | Target |
|---|---|---|---|---|
| E1 | Statement and branch coverage of the scoped business logic (register.py, the registration routes in admin.py, the register endpoints in api.py, `can_register()`, the two sanitize functions) | Functional | R1, R2, R3, R7 | 100%, with any uncovered line listed and justified |
| E2 | Every access-matrix check automated, and observed result equals expected result; dependency audit run on pinned versions with every finding recorded | Security | R4, R6 | 4 or more checks, 0 mismatches unexplained; 100% of findings recorded with package, version and fix |
| E3 | Inconsistency defects (R3) logged and each given a triage decision; no Critical or High defect still open without a decision | Functional | R3 | 0 untriaged defects, 0 open Critical or High without a documented decision |
| E4 | Performance of one registration operation at 5 simulated users | Performance | R2 | p95 and failure-rate limits to be set before testing, for example p95 at most 500 ms and under 1% unexpected failures. Justify the limits, and do not change them after seeing results. |

## 7. Assumptions
- Scores reflect the baseline (commit `9c276da`) and will be updated as defects are confirmed or fixed.
- Score values are judgement, not measurement. The group should agree them together.
- E4's limits are placeholders until one operation is chosen and a baseline measured.
