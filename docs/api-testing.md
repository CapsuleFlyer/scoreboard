# API tests and generated test data (area 2)

Files: `docs/api/openapi.yaml` (contract), `scripts/testdatagen.py` (generator), `tests/team/generated/api_cases.json` (committed generator output), `tests/team/test_api_generated.py` (tests that consume the generator), `tests/team/test_api_register.py` (rule-level API tests), `tests/team/test_testdatagen.py` (tests of the generator).

## Commands (PowerShell)
```
python scripts/testdatagen.py docs/api/openapi.yaml --out tests/team/generated/api_cases.json
python -m pytest tests/team/test_api_generated.py tests/team/test_api_register.py tests/team/test_testdatagen.py -q
```

## Change two constraints, regenerate, show the effect (brief section 2)
1. `copy tests\team\generated\api_cases.json before.json`
2. In `docs/api/openapi.yaml` change `team_name.maxLength` from 20 to 10 and `player1.minLength` from 1 to 3.
3. `python scripts/testdatagen.py docs/api/openapi.yaml --out after.json`
4. `python scripts/testdatagen.py --diff before.json after.json` lists the removed, added and re-classified values (for example length 21 removed, 11 added; a 2-character player name flips from valid to invalid).
5. `python -m pytest tests/team/test_api_generated.py -q`: the application still accepts 11-character team names, so the new "above max" cases FAIL. That is the effect: the spec changed, the tests followed, the code did not. Revert the spec (or change `api.py`) afterwards and regenerate.
`test_committed_generated_file_matches_the_spec` fails if the spec changes and the JSON is not regenerated.

## Coverage criteria used (state in the report which you can defend)
- Every input of both endpoints has EP classes (valid, empty, blank, missing, wrong type) and 3-point BVA on every length limit.
- Every documented status code (200, 400; 415 and 405 hand-written) is exercised; every error message branch in `api_register_team` is exercised in `test_api_register.py`.
- Repeated request (duplicate), read-back of the shared count after success and rejection, and no row written on rejection are asserted.

## Endpoint weaknesses to report (link to the risk register)
- DR-13 (new, UNCONFIRMED until the strict xfails are run): non-string JSON values and a `null` body crash with 500 instead of 400.
- DR-04 duplicate names are case-sensitive; DR-06 form and API disagree on required player names; DR-12 the API blueprint is CSRF-exempt and has no rate limit (READ).
- The tests use Flask's test client. The brief lists pytest with Requests; if the TA wants real HTTP, add a fixture that serves the app on a thread and swap `client.post` for `requests.post`.
