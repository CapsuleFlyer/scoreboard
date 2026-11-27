# Performance and recovery (area 3)

## Operation and limits (decide, then COMMIT THIS FILE BEFORE the first run)
Operation under test: `POST /api/register/team` (a state-changing write plus a capacity count), workflow W1.

| Limit | Proposed value | Why this value suits the operation |
|---|---|---|
| p95 response time | below 500 ms | a visitor presses "Register" and waits for the page: under half a second feels immediate, and the work is one insert and one count over a small table |
| Unexpected failures | below 1 % of requests | every request uses a unique team name and an open tournament, so no business rule should refuse it; any non-200 or `success:false` is unexpected. At the test's request rate 1 % is a handful of requests, so it still catches a real fault |

These are PROPOSALS. Change them if you can justify other values, then commit the file. The commit time shows the limits were set before the evidence was produced (brief section 5). Date and time set: TODO.

## Install k6 and run (PowerShell)
```
winget install k6        # or: choco install k6   (open a new terminal afterwards)
k6 version
python scripts/run_perf.py --p95 500 --max-fail 0.01
```
Runs one simulated user twice and five users twice. Each run starts a fresh server and database (`scripts/perf_server.py`), waits 10 s, then measures 60 s with all users running (`scripts/perf_register.js`). A full set takes about 6 minutes. Output in `docs/evidence/performance/`: `environment.txt`, `k6-<users>u-run<n>.txt` (raw k6 output), `summary-<users>u-run<n>.json` (k6 summary export), `results.md` (the table).

Close other heavy programs first and use the same machine, build and data for every run. Add `--measure 90` for longer runs.

## What the table reports (per run)
p95 in ms for the measured phase, requests completed per second (measured requests divided by 60 s), percentage of unexpected failures, teams registered, whether the server's count read back after the run equals what k6 saw succeed (shared-record check), and whether both limits held.

## Interpretation (write after the runs; do not pre-fill)
- Compare 1 user with 5 users: did p95 and throughput change, did failures appear?
- State the environment honestly: the Werkzeug development server with SQLite on one machine. The numbers describe that setup, not production.
- A run that breaches a limit is a finding: record it, its likely cause and the risk-register entry it belongs to.

## Failure and recovery test (`tests/team/test_recovery.py`)
A test double replaces `db.session.commit` and makes the database unavailable before the write completes.
1. Registration: first attempt answers 500, no team row, shared count unchanged. Database restored: retry gives 200 and exactly one team. Repeating the request gives 400 and no duplicate.
2. Admin confirmation: failed write leaves the team pending; after recovery the retry confirms it; repeating changes nothing.
3. DR-22 (suspected, strict xfail): the API answers a database failure with the default HTML 500 page, not a JSON error. Confirmed only when the test shows `xfailed`.

Run: `python -m pytest tests/team/test_recovery.py -v`
