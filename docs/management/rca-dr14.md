# Root Cause Analysis — DR-14: Input controller pages fail with NameError

**Defect:** [#15 — Input pages (iPad, remote, tournament, match) crash with NameError](https://github.com/CapsuleFlyer/scoreboard/issues/15)  
**Affected component:** Input blueprint  
**Severity / priority:** Major / P2  
**Category:** Missing dependency import  
**Status:** Root cause confirmed from current source; corrective change is not claimed as completed.

## Problem statement

Authenticated requests to the input controller's tournament, remote, iPad, and match pages can fail with HTTP 500. The affected routes call `db.get_or_404(...)`, but the input blueprint does not import the `db` object. Python therefore raises `NameError` when one of those route functions executes.

## 5 Whys

1. **Why do the input pages return HTTP 500?**  
   The route function raises a `NameError` while trying to access `db`.

2. **Why is `db` undefined in the route function?**  
   `app/blueprints/input.py` calls `db.get_or_404()` but its imports include Flask helpers and model classes, not `db`.

3. **Why does the route use a name that is not imported?**  
   The blueprint relies on the application-level SQLAlchemy database object but does not declare that dependency in its module imports.

4. **Why was the missing import not caught earlier?**  
   The input index route does not use `db.get_or_404()`, so a test that only checks `/input/` can pass while the affected detail routes remain untested.

5. **Why was route coverage incomplete?**  
   The input blueprint's route tests did not initially exercise each database-backed page with an existing tournament or match. The defect-specific strict expected-failure test was added to expose that gap.

## Fishbone analysis

| Cause area | Possible contributing cause |
|---|---|
| Code | The blueprint references the global SQLAlchemy `db` object without importing it. |
| Tests | Testing only the input index route does not execute the database lookup in the detail routes. |
| Process | A route-by-route smoke-test checklist was not applied when the input blueprint was separated into its own module. |
| Architecture | The application database object is defined in `app/__init__.py`; blueprints that use it must import it explicitly while avoiding circular imports. |
| Environment | The failure is deterministic when an affected route is reached; it is not dependent on a particular database record being missing. |
| People | No individual action is identified as the cause. The issue is a code dependency and test-coverage gap. |

## Root cause

The input blueprint has an undeclared module dependency. It calls `db.get_or_404()` in four route handlers but never imports `db` from the application package. As a result, Python cannot resolve the name when those routes execute.

The defect escaped earlier checks because the input index route can render without touching the undefined name, and the affected detail routes were not all covered by successful route-rendering tests.

## Corrective and preventive actions

1. Import the shared database object in `app/blueprints/input.py` using the project's established import pattern (for example, `from app import db`).
2. Add or retain tests that authenticate a client, create a tournament and match, and request each affected route:
   - `/input/tournament/<id>`
   - `/input/tournament/<id>/remote`
   - `/input/tournament/<id>/ipad`
   - `/input/match/<id>`
3. Assert that each route renders successfully for an existing record.
4. Keep separate tests for unauthenticated access and missing-record behaviour.
5. Run the focused input/authentication tests and the full test suite after the fix.

## Verification evidence and limitations

The current `app/blueprints/input.py` source imports `Blueprint`, `render_template`, `session`, model classes, and `login_required`, but not `db`. The four route handlers use `db.get_or_404()`. The test file `tests/team/test_auth_input_display.py` contains a strict xfail test named `test_input_pages_for_an_existing_record_render` covering those four routes, with the reason explicitly identifying DR-14.

**This document records the confirmed root cause and proposed actions; it does not claim that DR-14 has been fixed.** Close the defect only after the import is corrected and the route-rendering regression tests pass without xfail.
