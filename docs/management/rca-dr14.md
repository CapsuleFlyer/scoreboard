# Root cause analysis: DR-14, input pages crash with NameError (DRAFT)

Severity major, priority P2. Evidence: `tests/team/test_auth_input_display.py` (4 strict xfails); `input.py` covered at 72 % with 11 statements unreachable.

## 5 Whys
1. Why do `/input/tournament/<id>`, `/remote`, `/ipad` and `/input/match/<id>` return 500? They call `db.get_or_404` and raise `NameError`.
2. Why a NameError? `app/blueprints/input.py` never imports `db`.
3. Why was the import missing? The module was written or edited without importing the name it uses, and nothing runs the file before release.
4. Why was it not noticed? No upstream test requests these pages with an existing record (the first coverage run left them uncovered).
5. Why did no tool catch it? The CI pipeline had no check for undefined names, and the pages are only reached through the iPad pairing flow.

**Root cause:** no automated check for undefined names, and no test of the input pages.
The same cause produced DR-15 (`sanitize_message` used in `api.py` but not imported).

## Fishbone (cause categories)
| Category | Contributing cause |
|---|---|
| Code | missing `from app import db` (and a missing import in `api.py`) |
| Tests | no test reached the affected routes; coverage 48 % on this file at baseline |
| Tools | no linter rule for undefined names in CI |
| Process | the pages are reached only by a manual pairing flow, so no one exercised them |
| Method | no rule to run every route once before merging |

## Actions
- Corrective: add the missing imports; remove the four xfails in `test_auth_input_display.py` and the two DR-15 xfails in `test_api_match_display.py` in the same change.
- Preventive: add an undefined-name check to CI (for example ruff rule F821 or pyflakes over `app/`); keep route-level tests for every blueprint (now in place, 98 % whole-app coverage).
