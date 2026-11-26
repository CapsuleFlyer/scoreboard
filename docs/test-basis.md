# Test Basis: Team Registration and Management

Project: SE3002 Final Project, Fall 2026. Status: DRAFT, verified against source on 2026-11-19.

## 1. System under test
- Upstream: https://github.com/McShoothy/scoreboard (MIT licence)
- Fork: https://github.com/CapsuleFlyest/scoreboard
- Baseline commit (tag `baseline`): 9c276da06a16356ce4be330a0b990dbddd4873f8
- Stack: Flask 3.0.0, Flask-SQLAlchemy, SQLite, Flask-SocketIO, Flask-WTF (CSRF)
- Verification legend used below: **RUN** = executed against the code, **READ** = read in source only, **TODO** = not yet verified.

## 2. Setup (PowerShell, Windows, Python 3.12, no venv)
| Step | Command | Status |
|---|---|---|
| Install | `python -m pip install -r requirements.txt` (drop gevent, gevent-websocket, eventlet, gunicorn if they fail) | TODO on Windows |
| Seed | `python scripts/seed_admin.py` (sets admin / `password`) | RUN (Linux) |
| Start | `python -m flask --app run run` then http://localhost:5000 | TODO on Windows |
| Reset | stop app, delete `tournament.db`, rerun the seed script | TODO on Windows |
| Run tests | `python -m pytest -q` then `git checkout bracket_test_output.json` | TODO on Windows |

## 3. Scope
In scope, two workflows in one module:
1. **W1 Public registration**: `/register/*` (app/blueprints/register.py) and the JSON twin `/api/register/validate-code`, `/api/register/team` (app/blueprints/api.py).
2. **W2 Admin registration management**: under `/admin/tournament/<id>/...` (app/blueprints/admin.py): registrations page, confirm, reject, check-in, manual add, and registration toggle (see decision D1).

Out of scope (list in the test plan): bracket generation, start tournament, TV display, iPad scoring, Socket.IO events, external token API.

| Workflow | Starting condition | User action | Expected outcome |
|---|---|---|---|
| W1 | Tournament open, status `registration`, not full | Submit valid team form | Team row created; confirmed unless `require_confirmation` |
| W2 | Pending team exists, admin logged in | Confirm it | `is_confirmed = True`, JSON success |

**Shared record:** the tournament's team count versus `max_teams`. W1 increases it; W2 reject decreases it; W2 manual add increases it. All three read it.

## 4. Requirements
| ID | Requirement | Where | Status |
|---|---|---|---|
| FR1 | Valid code opens the registration page; empty or unknown code shows an error and redirects | register.py `register_join`, `register_tournament` | READ |
| FR2 | Valid registration creates a team, confirmed immediately unless `require_confirmation` | `register_team` | RUN |
| FR3 | Registration refused when closed, tournament not in `registration`, past deadline, or full | `Tournament.can_register` | RUN (see N1) |
| FR4 | Duplicate team name in same tournament refused | `register_team` | RUN (case-sensitive) |
| FR5 | Player names / email required only when the tournament requires them (form) | `register_team` | READ, but see N2 |
| FR6 | Anonymous visitor cannot reach admin registrations page or actions | `login_required` | RUN: 302 to `/login?next=...` (CSRF disabled in test config) |
| FR7 | Admin can confirm a pending team | `admin_confirm_team` | RUN |
| FR8 | Admin can reject a team (row deleted, slot freed) | `admin_reject_team` | READ |
| FR9 | Admin can toggle check-in | `admin_checkin_team` | READ |
| FR10 | Admin can add a team manually; refused when full or duplicate | `admin_add_team_to_tournament` | RUN |
| FR11 | Team must belong to the tournament in the URL, else 400 | confirm / reject / check-in | READ |
| FR12 (D1) | Admin can open/close registration | `admin_toggle_registration` | READ |

## 5. Business rules
1. **Boundary**: team name 1-20 chars (form and API). Registered count `>= max_teams` refuses. RUN: 0 chars refused, 20 accepted, 21 refused.
2. **Decision**: `can_register()` checks in order (first failure wins, which decides the message): `registration_open`; `status == 'registration'`; `registration_deadline and now > deadline`; `count >= max_teams`. Treat the deadline term as two atomic conditions (set, passed), giving five.
3. **State change**: team `is_confirmed = not require_confirmation` on creation; pending to confirmed by admin; confirm on a confirmed team is accepted (200, idempotent); check-in is an independent toggle; reject deletes from any state; manual add creates a confirmed team.
4. **Conditional fields**: form requires player names (max 30 each) only if `require_player_names`; email required only if `require_email`.

## 6. Roles
- **Anonymous registrant**: W1 only. RUN: anonymous GET of the registrations page and POST to confirm both 302 to `/login`.
- **Admin** (session login): W2. `Admin` has no role column (READ), so all admins are equal. Justified assumption: single admin role.
- READ: registration routes do not check `Tournament.owner_id`; the tournament list does filter by owner (admin.py:151). Any admin can manage any tournament's registrations.

## 7. Assumptions to record
- A1: "Reject" means delete (there is no rejected state in the model).
- A2: Duplicate names should be case-insensitive (admin add does this; public form does not, see F3).
- A3: Max 20 characters for team names is the intended rule for public registration (documented only in code and error text).
- A4 (**corrects the draft**): the cap counting pending teams is not an assumption. `get_registered_team_count()` counts every team row, so it is code behaviour (RUN: with `max_teams=1` and `require_confirmation`, one pending team made the tournament full).
- A5: "100% coverage of all server-side business logic" means the WHOLE application, not only the two workflows. Confirmed by the TA (as reported by the member; TODO: add the date and keep the written reply as evidence). The scoped report (`scripts/scoped_coverage.py`) stays as a secondary figure; the whole-app figure from `coverage.json` is now the headline. Measured on 2026-11-24 from `tests/team` only: 38 % of statements (712 of 1630).

## 8. Findings (re-confirmed)
| # | Finding | Status |
|---|---|---|
| F1 | README default login `admin/password` fails: stored scrypt hash matches none of password, admin, admin123, changeme, empty | RUN (hash check) |
| F2 | 404 handler renders `url_for('ui.index')`, which does not exist, so every 404 is a 500. Confirming a nonexistent team (`get_or_404`) returns 500 | RUN |
| F3 | Inconsistent rules: public form accepts "Alpha" and "alpha" in the same tournament; admin add truncates team name to 8 chars (`Robotics Club` became `Robotics`) and player names to 10 (`Bartholomew Jones` became `Bartholome`), case-insensitive duplicate check | RUN |
| F4 | Confirm on an already confirmed team returns 200; reject deletes; check-in toggles | confirm RUN, others READ |
| F5 | `max_teams = None` makes `can_register()` raise TypeError. **Correction**: not reachable through the app. The create form always sets an int (default 16), and a plain `None` at insert is replaced by the column default. Only reproducible by updating the row to NULL after creation. Latent, low severity | RUN |
| F6 | Anonymous POST to confirm: 400 from CSRF (your earlier run) versus 302 to `/login` with CSRF disabled (my run). Both are plausible; observe with a real CSRF token in the Playwright access check | TODO |
| F7 | pip-audit on the pinned packages: 14 unique advisories across Flask 3.0.0, Werkzeug 3.0.1, python-socketio 5.10.0, python-engineio 4.8.1, python-dotenv 1.0.0 (25 rows printed because of duplicates). Rerun on your machine and save the raw output as evidence | RUN (Linux), redo on Windows |
| F8 | Socket.IO `cors_allowed_origins="*"`; `api`, `external_api`, `input_bp` are CSRF-exempt | READ |

### New findings (not in the earlier draft)
| # | Finding | Status |
|---|---|---|
| N1 | **Deadline crash.** `utc_now()` is timezone-aware but SQLite returns naive datetimes, so once `registration_deadline` is set and the row is reloaded, `can_register()` raises TypeError. Result: GET `/register/tournament/<code>`, POST `/register/team`, POST `/api/register/validate-code` and `/api/register/team` all return 500. No route or template sets the deadline, so it is only reachable by editing the database; treat as latent, medium. It also means the "deadline passed" branch cannot be covered through normal flows; unit tests need a transient object or a fix | RUN |
| N2 | Form and API disagree: the API always requires both player names, the form only if `require_player_names`. When not required, the form stores empty strings | API READ, form RUN |
| N3 | Admin add does not call `can_register()`, so it works when registration is closed or the tournament has started. Check-in does not require the team to be confirmed | READ |
| N4 | Pending teams consume slots, but the public team list shows only confirmed teams, so a "full" tournament can display no teams. Anonymous registrations can therefore fill the cap before admin approval (I did not look for rate limiting) | count RUN, rest READ |

## 9. Open decisions for the group
- D1: include `admin_toggle_registration` in W2? It is a short, cheap way to drive the "closed" path of rule 2.
- D2: which entry point(s) does the API test area target? The `/api/register/*` JSON endpoints are CSRF-exempt and easiest for `requests`; the form routes need a CSRF token first.
