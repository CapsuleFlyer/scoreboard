# Mutation analysis (area 1)

Tool: `scripts/mutate_rules.py` (AST mutants, 4 custom operators). Scope: `app/models.py:173-191` and `app/blueprints/api.py:579-658`.

## First run (RUN on Windows, 2026-11-24)
Score 86.2 %: 94 of 109 mutants killed, 15 survived.

| Operator | Kind | Mutants | Killed |
|---|---|---|---|
| limit_shift | custom (rule 1 length limits) | 6 | 6 |
| confirmation_flip | custom (rule 3) | 2 | 2 |
| capacity_ignore_pending | custom (rule 1 / A4) | 1 | 1 |
| check_order_swap | custom (rule 2 order of checks) | 7 | 4 |
| cmp_boundary, bool_swap, not_removal, int_shift | standard | 10 + 7 + 6 + 20 | all killed |
| str_mutation | standard | 50 | 38 |

## The 15 survivors
No survivor is an equivalent mutant: each changes something a client can see (a JSON key, an error text, the order of messages, a socket event). All 15 are killable. DRAFT classification, verify each against the code before the viva.

| # | Line | Mutation | Class | Why it survived | Killed by (`test_api_register_strict.py`) |
|---|---|---|---|---|---|
| 17 | 618 | swap name and player 1 guards | missing test | tests only ever sent one invalid field, so order never mattered | `test_team_name_is_reported_before_player1` |
| 18 | 621 | swap player 1 and player 2 guards | missing test | same | `test_player1_is_reported_before_player2` |
| 19 | 624 | swap player 2 and email guards | missing test | same | `test_player2_is_reported_before_missing_email` |
| 44 | 648 | event name `team_registered` changed | missing test | nothing listened to the socket | `test_success_emits_team_registered_*` |
| 70 | 649 | payload key `tournament_id` changed | missing test | same | same |
| 71 | 650 | payload key `team` changed | missing test | same | same |
| 91 | 616 | `success` key on the rule-2 rejection | weak assertion | only status and `error` were checked | `test_rule_2_rejection_has_the_exact_body` |
| 94 | 619 | `error` key on the team-name rejection | weak assertion | generated tests checked status and `success` only | `test_field_rejection_names_the_field_to_correct` |
| 95 | 619 | team-name message text | weak assertion | message never asserted | same |
| 97, 98 | 622 | player 1 `error` key, message | weak assertion | same | same |
| 100, 101 | 625 | player 2 `error` key, message | weak assertion | same | same |
| 102 | 628 | `success` key on the missing-email rejection | weak assertion | only `error` was checked | `test_missing_email_rejection_has_the_exact_body` |
| 105 | 632 | `success` key on the duplicate rejection | weak assertion | only `error` was checked | `test_duplicate_rejection_has_the_exact_body` |

Reading: the 12 surviving string mutants and 3 order mutants were all in the API's rejection paths, where the earlier tests asserted status codes but not the full body. That matters for usability (FR: the error must say what to correct), so the new tests compare whole bodies.

## Second run (RUN on Windows, 2026-11-24)
Command: `python scripts/mutate_rules.py --only app/models.py:173-191 --only app/blueprints/api.py:579-658 --out mutation-report-2.json`

Score 100.0 %: 109 of 109 mutants killed, 0 survived (first run: 86.2 %). The 15 survivors above were killed by the 13 tests in `tests/team/test_api_register_strict.py`; no production code was changed. Limits of this number: it covers only `can_register()` and `api_register_team`, not the whole app, and a high score shows the tests notice these mutations, not that every defect would be found (the operators cannot invent faults they do not model).

## Threshold for the CI gate
Gate: **95 %** (`--min-score 95` in `.github/workflows/team-quality-gate.yml`), reason in `docs/ci-gate.md`.
