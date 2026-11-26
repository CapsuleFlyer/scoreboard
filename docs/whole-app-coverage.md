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
| `blueprints/external_api.py` | `test_external_api.py` |
| `blueprints/auth.py`, `main.py`, `input.py`, `display.py` | `test_auth_input_display.py`, `test_sanitizers_auth_models.py` |
| `blueprints/socket_events.py` | `test_socket_utils_models.py` |
| `blueprints/bracket.py` | exercised through `test_admin_management.py` (create and start for all formats) and `test_api_match_display.py` (bracket self-test); gaps TODO after the first run |
| `models.py`, `utils.py` | `test_socket_utils_models.py`, `test_sanitizers_auth_models.py`, `test_can_register.py` |

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
