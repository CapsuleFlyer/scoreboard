# Root cause analysis: DR-03, registration page and API crash once a deadline is set (DRAFT)

Severity major, priority P2, issue #3. Evidence: `tests/team/test_can_register.py` (strict xfail), unit and browser runs.

## 5 Whys
1. Why does the registration page return 500 when a deadline is set? `Tournament.can_register()` raises `TypeError`.
2. Why a TypeError? It compares `datetime.now(timezone.utc)` (timezone-aware) with `registration_deadline` (naive).
3. Why is the deadline naive? The column is a plain `DateTime`; SQLite stores no timezone, so the value comes back naive.
4. Why did the code assume otherwise? The comparison was written against the timezone-aware clock without a rule for how stored times are read.
5. Why was it not caught? No upstream test ever sets a deadline, and there is no project convention for naive versus aware datetimes.

**Root cause:** no datetime convention, and no test for the deadline branch.

## Fishbone (cause categories)
| Category | Contributing cause |
|---|---|
| Method | no rule that stored times are UTC and how to read them |
| Code | aware clock compared with a naive column value |
| Tests | the deadline branch of `can_register()` had no test |
| Tools | no check for naive/aware mixing; SQLite hides the problem until a value is read back |
| Process | review did not ask what happens when the optional deadline is set |
| Environment | tests used in-memory SQLite with no deadline |

## Actions
- Corrective: treat stored deadlines as UTC when comparing (for example `deadline.replace(tzinfo=timezone.utc)` when naive); remove the xfail in `test_can_register.py` in the same change.
- Preventive: one helper for "now" and for reading stored times; a test for every optional date; keep the strict xfail until fixed.
- Same root cause elsewhere: DR-16 (`APIToken.validate_token`). Fix both with the same helper.
