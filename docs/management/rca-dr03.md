# Root Cause Analysis — DR-03: Registration deadline causes a datetime comparison error

**Defect:** [#3 — Registration page and API crash once a deadline is set](https://github.com/CapsuleFlyer/scoreboard/issues/3)  
**Affected requirement:** FR3  
**Severity / priority:** Major / P2  
**Category:** Date-time handling  
**Status:** Root cause analysis based on the reported reproduction and current source; corrective change is not claimed as completed.

## Problem statement

When a tournament has a registration deadline saved in the database, registration requests can fail with a server error instead of allowing registration before the deadline and refusing it after the deadline. The reported exception is:

`TypeError: can't compare offset-naive and offset-aware datetimes`

The affected decision is in `Tournament.can_register()` in `app/models.py`. It compares the deadline loaded from the database with `utc_now()`, which returns a timezone-aware UTC datetime.

## 5 Whys

1. **Why do registration requests return HTTP 500 when a deadline is set?**  
   The deadline comparison raises a `TypeError` before the registration decision can return its normal result.

2. **Why does the comparison raise a `TypeError`?**  
   The value read back for `registration_deadline` is timezone-naive, while `utc_now()` returns a timezone-aware datetime.

3. **Why are the two datetime values different in timezone awareness?**  
   The SQLAlchemy `DateTime` column is not configured with timezone-aware storage semantics that are preserved by the SQLite database used in the reported test setup. SQLite-backed values can be returned without timezone information even if the original value was timezone-aware.

4. **Why does application logic assume the database value can be compared directly with an aware UTC value?**  
   The model's deadline check does not normalize or validate the timezone awareness of a value after it is loaded from persistence.

5. **Why was this not caught before the defect was reported?**  
   The ordinary registration path does not set a deadline through the UI, so routine tests and manual flows can exercise registration without reaching the deadline comparison. The edge case requires a persisted deadline to be present.

## Fishbone analysis

| Cause area | Possible contributing cause |
|---|---|
| Code | `can_register()` directly compares a persisted deadline with an aware UTC timestamp without normalizing the persisted value. |
| Data / persistence | SQLite does not reliably preserve timezone metadata for a SQLAlchemy `DateTime` value. |
| Tests | Registration tests that omit a saved deadline do not execute the failing comparison. A regression test must persist and reload a deadline before calling the registration routes. |
| Process | The deadline feature's persistence behaviour was not explicitly included in the registration test scenarios. |
| Environment | The defect is reproducible with the SQLite test configuration; database backends may differ in how timezone information is handled. |
| People | No individual action is identified as the cause. The issue is a gap in the design and verification process. |

## Root cause

The registration deadline comparison relies on timezone information surviving a database round trip. In the reported SQLite setup, the persisted deadline is returned as a naive datetime, but the comparison uses an aware UTC datetime. The application does not normalize both operands to a common timezone convention before comparing them.

The lack of a regression test that saves and reloads a deadline allowed the defect to remain outside the normal registration test path.

## Corrective and preventive actions

1. Establish one explicit convention for persisted deadlines (UTC) and enforce it at the persistence boundary or immediately before comparison.
2. If a naive value is encountered, handle it according to the documented storage convention rather than comparing it directly with an aware value. Do not silently assume a local timezone.
3. Add a model-level test that saves a deadline, commits, reloads the tournament, and checks registration both before and after the deadline.
4. Add route-level tests for the registration page and both registration API endpoints using a persisted deadline.
5. Run the focused registration tests and the full test suite after the correction.

## Verification evidence and limitations

The defect report records reproduction on Windows and identifies `Tournament.can_register()` in `app/models.py` as the failing comparison. The current source defines `utc_now()` as `datetime.now(timezone.utc)` and uses it in the deadline comparison. This supports the timezone-awareness mismatch described above.

**This document records the analysis and proposed actions; it does not claim that DR-03 has been fixed.** Close the defect only after the persisted-deadline regression tests pass and the affected registration routes return the expected responses.
