# CI quality gate (area 1)

Workflow: `.github/workflows/team-quality-gate.yml`, runs on every pull request. Three jobs; each is a required status check.

| Job | What it enforces | Threshold (PROVISIONAL) | Where the number must come from |
|---|---|---|---|
| `tests-and-coverage` | all `tests/team` tests pass; scoped coverage of the in-scope code | statements >= 90 %, branches >= 85 % | first measured run on your machine; the justification is yours: say why not 100 % (for example DR-03 makes the deadline branch unreachable through normal flows) |
| `mutation` | mutation score on `models.py` rule code and the API register code | >= 95 % (set 2026-11-24) | runs: 86.2 % before, 100.0 % (109/109) after killing the 15 survivors; reason below |
| `sonar` | SonarCloud quality gate (waits for the result) | gate defined in SonarCloud | SonarCloud accepted as "SonarQube" by the TA (as reported by the member; TODO: date and keep the reply) |

No step uses a switch that hides failures, and every step's exit code decides the job.

## Why the mutation threshold is 95 %
- Evidence: the first run scored 86.2 % (15 of 109 survived). Every survivor was killable and was killed by new tests, so the second run reached 100.0 % (109/109). 100 % is what the tests achieve now.
- Why not 100 %: a gate at exactly 100 % would block any pull request that adds a single mutant the tests miss, even for a harmless reason such as a new message string. With 109 mutants, 95 % allows at most 5 survivors (5 survivors = 95.4 %, pass; 6 = 94.5 %, fail). That is small enough to catch a real weakening of the tests and loose enough that one new line does not stop unrelated work.
- Why not the old 70 %: that is far below the measured 86.2 % even before the tests were improved. A drop from 100 % to 75 % would still have passed, so it would not have protected the business rules.
- The threshold applies to the 109 mutants of `can_register()` and the API register function. If you widen the scope later, rerun, and re-set it from the new measurement.

## When the pipeline runs
- Every push to a branch with an open pull request starts a run; a newer push cancels the older run of the same branch (`concurrency`).
- `tests-and-coverage` and `sonar` run on every pull request and on pushes to `main`/`master` (the push run gives SonarCloud its main-branch analysis).
- `mutation` takes over an hour, so it runs on every non-draft pull request only. Work in progress goes in a draft pull request; "Ready for review" starts the full gate, and merging needs all three checks (a skipped job counts as passed in GitHub's required checks, and a draft cannot be merged). **Confirm with the TA** that this satisfies "GitHub Actions on every pull request".

## One-time GitHub setup (cannot be done by a patch)
1. Repo Settings > Secrets and variables > Actions > new secret `SONAR_TOKEN` (a new token; never paste it in chat or commit it).
2. SonarCloud: keep "Automatic analysis" off.
3. Settings > Branches > add a rule for the default branch: "Require a pull request", "Require status checks to pass before merging", select `tests-and-coverage`, `mutation`, `sonar`. Without this the gate does not actually block merging.
4. Pull requests from a fork have no access to secrets, so `sonar` fails there. Open PRs from a branch inside your own repository.

## Evidence the brief asks for (you produce it; nothing here is pre-made)
- **Fix PR (fails before, passes after):** suggested: fix DR-05 (`sanitize_team_name` 8 to 20, `sanitize_player_name` 10 to 30). On the PR branch first commit only the change to `tests/team/test_admin_registration.py` that removes the DR-05 xfail marker (CI fails), then commit the fix (CI passes). Link both runs.
- **Blocked PR:** open a PR that removes an assertion or changes `>=` to `>` in `can_register`; the mutation or coverage job must fail and the PR must show "merging is blocked". Screenshot the PR and link the run. Do not merge it.

First pipeline run: see the PR.
