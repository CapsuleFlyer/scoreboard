# Whole-application coverage (area 1)

The TA confirmed that "100 % statement and branch coverage of all server-side business logic" means the whole app. Scoped coverage (`scripts/scoped_coverage.py`) stays as a secondary figure.

## How to measure
```
python -m pytest tests/team --cov --cov-report=term-missing --cov-report=json
python scripts/scoped_coverage.py
```
Only tests in `tests/team/` count (upstream tests earn no marks). `.coveragerc` measures `app/*` with branch coverage.

## Files and the tests that cover them
| File | Tests |
|---|---|
| `blueprints/register.py` | `test_register_routes.py`, `test_can_register.py` |
| `blueprints/admin.py` | `test_admin_registration.py` (registration routes), `test_admin_management.py` (the rest) |
| `blueprints/api.py` | `test_api_register*.py`, `test_api_generated.py` (registration), `test_api_match_display.py` (the rest) |
| `blueprints/external_api.py` | `test_team_external_api.py` |
| `blueprints/auth.py`, `main.py`, `input.py`, `display.py` | `test_auth_input_display.py`, `test_sanitizers_auth_models.py` |
| `blueprints/socket_events.py` | `test_socket_utils_models.py` |
| `blueprints/bracket.py` | exercised through `test_admin_management.py` (create and start for all formats) and `test_api_match_display.py` (bracket self-test); gaps TODO after the first run |
| `models.py`, `utils.py` | `test_socket_utils_models.py`, `test_sanitizers_auth_models.py`, `test_can_register.py` |

## What each coverage number measures (read this before quoting a percentage)
| Number | Where it comes from | What it covers |
|---|---|---|
| WHOLE APP (headline) | pytest-cov `TOTAL`, `coverage.json` totals | every statement and branch of `app/*`: 1822 statements, 516 branches. Same denominator in every run |
| SCOPED | `scripts/scoped_coverage.py` | only the line ranges in its `SCOPE` table (the registered workflows: 206 statements, 68 branches). It was never the source of the whole-app percentage |
| SonarCloud coverage | `coverage.xml` uploaded by the CI job | whole project, from `tests/team` only; it can differ slightly from pytest-cov because Sonar counts lines and conditions its own way |

The whole-app figure of 98 % on 2026-11-26 (471 passed, 40 xfailed) and the scoped figure of 100 % are both real and measure different things. A drop in the whole-app figure with the SAME 1822 statements means fewer tests ran, not that the scope changed.

Reproduce with one command (writes the HTML report, `coverage.xml` for Sonar and `coverage.json`, prints whole-app, scoped and suite results, and marks the figures UNTRUSTED if the suite is not green):
```
python scripts/coverage_report.py
```
Do not run a bare `pytest`: it collects the upstream tests and the browser tests too. Two of our files once reused the file names of upstream tests (`test_external_api.py`, `test_security_access.py`), which makes pytest stop at collection with "import file mismatch" and run nothing. They are now `test_team_external_api.py` and `test_e2e_security_access.py`, and `test_collection_guard.py` fails if a name is ever reused.

## Results (fill in from YOUR run; do not copy numbers from anywhere else)
| Date | Statements | Branches | Command output file |
|---|---|---|---|
| 2026-11-24 (before this work) | 38 % (712/1630) | see report | `coverage.json` |
| 2026-11-26 (final run) | TOTAL 98 % (coverage.py statement+branch figure); 21 of 1822 statements missed | 18 partial branches of 516 | `pytest-run.txt`, `coverage.json` (469 passed, 40 xfailed, 0 failed) |

`bracket.py` was not in the first report because no test in `tests/team` imported it. Once it is imported the denominator grows, so the percentage can fall even though more code is tested.

## Uncovered code that is defended (fill in after the run)
| Lines | Why they cannot be covered | Defect |
|---|---|---|
| `input.py` bodies after `db.get_or_404` | the line raises NameError before the rest runs | DR-14 |
| `bracket.py` 84-92 | round 1 is padded with byes at the end, so "team 2 present, team 1 missing" cannot happen | none (dead code) |
| `bracket.py` 49->47, 66->68, 68->72, 76->62, 78->62, 99->104, 100->99 | guards that are always true for any team count (every non-final match has a next match; the padded list always has `bracket_size` entries) | none (dead code) |
| `bracket.py` 174->172, 183->182, 187, 190->195, 191->190 | double elimination setup branches no team count reaches | none (dead code) |
| `bracket.py` 237->exit, 315->exit, 363->exit | "no first match" checks right after matches were created | none (dead code) |
| `models.py` 360 | token-expiry return: the comparison raises first | DR-16 |
| `app/__init__.py` 27->30 | `werkzeug.serving` is always imported by Flask in a test run, so the gevent branch only runs in production | none (environment) |
