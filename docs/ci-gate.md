# CI quality gate (area 1)

Workflow: `.github/workflows/team-quality-gate.yml`, runs on every pull request. Three jobs; each is a required status check.

| Job | What it enforces | Threshold (PROVISIONAL) | Where the number must come from |
|---|---|---|---|
| `tests-and-coverage` | all `tests/team` tests pass; scoped coverage of the in-scope code | statements >= 90 %, branches >= 85 % | first measured run on your machine; the justification is yours: say why not 100 % (for example DR-03 makes the deadline branch unreachable through normal flows) |
| `mutation` | mutation score on `models.py` rule code and the API register code | >= 70 % | first full run of `scripts/mutate_rules.py`; set it just under the score you reach after killing the killable survivors, and justify |
| `sonar` | SonarCloud quality gate (waits for the result) | gate defined in SonarCloud | **TODO ask the TA** whether SonarCloud counts as "SonarQube" |

No step uses a switch that hides failures, and every step's exit code decides the job.

## One-time GitHub setup (cannot be done by a patch)
1. Repo Settings > Secrets and variables > Actions > new secret `SONAR_TOKEN` (a new token; never paste it in chat or commit it).
2. SonarCloud: keep "Automatic analysis" off.
3. Settings > Branches > add a rule for the default branch: "Require a pull request", "Require status checks to pass before merging", select `tests-and-coverage`, `mutation`, `sonar`. Without this the gate does not actually block merging.
4. Pull requests from a fork have no access to secrets, so `sonar` fails there. Open PRs from a branch inside your own repository.

## Evidence the brief asks for (you produce it; nothing here is pre-made)
- **Fix PR (fails before, passes after):** suggested: fix DR-05 (`sanitize_team_name` 8 to 20, `sanitize_player_name` 10 to 30). On the PR branch first commit only the change to `tests/team/test_admin_registration.py` that removes the DR-05 xfail marker (CI fails), then commit the fix (CI passes). Link both runs.
- **Blocked PR:** open a PR that removes an assertion or changes `>=` to `>` in `can_register`; the mutation or coverage job must fail and the PR must show "merging is blocked". Screenshot the PR and link the run. Do not merge it.
