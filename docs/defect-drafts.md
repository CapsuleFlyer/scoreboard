# Defect drafts (ready to paste into GitHub Issues)

Created from the verified findings in `docs/test-basis.md`. Severity, priority and triage are proposals for the group to review, and each member should be able to defend them.
Evidence: RUN = executed against the code, READ = read in the source only (those stay `status:new` until a test confirms them).
Create the labels from `docs/defect-management.md` first. Paste each block into a new issue using the "Defect" template. After creating each issue, write its real GitHub number next to the draft ID below, because the traceability matrix needs it.

---

## DR-01 README default login does not work
- Summary: the README says to log in as `admin` / `password`, but that login fails on a fresh database.
- Steps: 1. Delete `tournament.db`. 2. Start the app. 3. Open `/login` and enter `admin` / `password`.
- Expected: login succeeds, as documented in README "Default Login".
- Actual: the stored scrypt hash in `app/__init__.py` matches none of `password`, `admin`, `admin123`, `changeme`, or an empty password.
- Evidence: RUN (hash check against five candidates). Workaround in our repo: `scripts/seed_admin.py`.
- Severity: minor. Priority: P2. Category: config-docs. Requirement: prerequisite for the admin role (FR6 to FR12). Risk: none (setup).
- Triage: fix later (correct the README or the seeded hash; keep our seed script for tests).

## DR-02 Every 404 returns a 500
- Summary: the 404 handler renders a template that links to a nonexistent endpoint, so any "not found" crashes with a 500.
- Steps: 1. Start the app. 2. GET `/nonexistent`. 3. As a logged-in admin, POST `/admin/tournament/<id>/team/999/confirm`.
- Expected: 404 page. The second request should return 404.
- Actual: HTTP 500 both times. `app/templates/404.html` calls `url_for('ui.index')`, which does not exist (the endpoint is `main.index`).
- Evidence: RUN (500 observed; the error says "Did you mean 'main.index'").
- Severity: major. Priority: P2. Category: error-handling. Requirement: FR7 to FR9 (nonexistent team). Risk: R5.
- Triage: fix now (one-line change), then add a regression test.

## DR-03 Registration page and API crash once a deadline is set
- Summary: `Tournament.can_register()` compares a timezone-aware time with a naive time loaded from SQLite, which raises TypeError.
- Steps: 1. Set `registration_deadline` on a tournament (no UI sets it, so use the database or a test). 2. Reload the tournament. 3. GET `/register/tournament/<code>`, POST `/register/team`, POST `/api/register/validate-code`, POST `/api/register/team`.
- Expected: registration works before the deadline and is refused after it ("Registration deadline has passed").
- Actual: all four requests return 500 (`TypeError: can't compare offset-naive and offset-aware datetimes`, `app/models.py` line 187).
- Evidence: RUN.
- Severity: major. Priority: P2. Category: date-time. Requirement: FR3. Risk: R1.
- Triage: fix later (reachable only if a deadline is set directly in the database), but the fix is needed to reach 100% branch coverage of `can_register()` through real data.

## DR-04 Duplicate team names are case-sensitive on the public form and API
- Summary: "Alpha" and "alpha" can both register in the same tournament.
- Steps: 1. Register "Alpha". 2. Register "alpha" in the same tournament.
- Expected (assumption A2): the second registration is refused as a duplicate, as admin manual add already does.
- Actual: both teams are created.
- Evidence: RUN (form). The API uses the same check (READ).
- Severity: minor. Priority: P3. Category: validation. Requirement: FR4. Risk: R3.
- Triage: needs more information (confirm A2 with the TA), then fix.

## DR-05 Admin manual add silently truncates names
- Summary: manual add cuts the team name to 8 characters and player names to 10, with no warning, while the public form allows 20 and 30.
- Steps: 1. As admin, POST `/admin/tournament/<id>/team/add` with name "Robotics Club" and player1 "Bartholomew Jones".
- Expected: the team is saved as entered or rejected with a clear message.
- Actual: success response; stored name "Robotics", player1 "Bartholome".
- Evidence: RUN. Inferred from the code, not run: two different names with the same first 8 characters, such as "Robotics Club" and "Robotics Team", would collide as duplicates.
- Severity: major. Priority: P2. Category: validation. Requirement: FR10. Risk: R3.
- Triage: fix later (align limits across the three entry points).

## DR-06 Form and API disagree on player-name rules
- Summary: the API always requires both player names; the form requires them only if the tournament sets `require_player_names`.
- Steps: 1. Use a tournament with `require_player_names` off. 2. Register through the form without player names. 3. Register through `/api/register/team` without player names.
- Expected: the same rule at every entry point (FR5).
- Actual: the form accepts the team and stores empty strings; the API returns 400.
- Evidence: form RUN (empty strings stored); API READ.
- Severity: minor. Priority: P3. Category: validation. Requirement: FR5. Risk: R3.
- Triage: fix later.

## DR-07 Admin manual add ignores closed or started tournaments
- Summary: `admin_add_team_to_tournament` checks only duplicates and the cap, not `can_register()`.
- Steps: 1. Close registration or start the tournament. 2. As admin, POST the add-team request.
- Expected (needs a decision): refuse with a clear message, or document that admins may add teams at any time.
- Actual (from the code): the team is created if the name is unique and the cap isn't reached.
- Evidence: READ only. Not run yet.
- Severity: major. Priority: P2. Category: state-rules. Requirement: FR3, FR10. Risk: R7.
- Triage: needs more information, then write a test to confirm.

## DR-08 Pending teams use up capacity but are hidden from the public list
- Summary: the cap counts all teams, including unconfirmed ones, while the public page lists only confirmed teams.
- Steps: 1. Create a tournament with `max_teams` 1 and `require_confirmation` on. 2. Register one team. 3. Open the public page.
- Expected (assumption): the cap should count confirmed teams, or the page should explain why it is full.
- Actual: registration is refused with "Tournament is full" while the public list shows no teams.
- Evidence: RUN (count 1, confirmed 0, `can_register()` returns "Tournament is full").
- Severity: minor. Priority: P3. Category: state-rules. Requirement: FR2, FR3. Risk: R2.
- Triage: needs more information (this may be intended behaviour).

## DR-09 Weak state transitions for confirm, reject and check-in
- Summary: confirming an already confirmed team returns 200, reject deletes the team (there is no rejected state), and check-in works on unconfirmed teams.
- Steps: 1. As admin, POST confirm twice for the same team. 2. POST check-in on a pending team.
- Expected: invalid transitions are refused or documented.
- Actual: confirm returns 200 both times. Check-in on a pending team is accepted (from the code).
- Evidence: confirm RUN; check-in READ.
- Severity: minor. Priority: P3. Category: state-rules. Requirement: FR7 to FR9. Risk: R7.
- Triage: fix later, or document as accepted behaviour.

## DR-10 Pinned dependencies have known vulnerabilities
- Summary: pip-audit reports 14 unique advisories across five pinned packages.
- Evidence: RUN on Linux against the pinned versions. Rerun on Windows and save the raw output.
  - Flask 3.0.0: PYSEC-2026-2151 (fixed in 3.1.3)
  - python-socketio 5.10.0: PYSEC-2026-1854, PYSEC-2026-3042 (fixed in 5.14.0, 5.16.2)
  - python-engineio 4.8.1: PYSEC-2026-3032, PYSEC-2026-3033 (fixed in 4.13.2)
  - Werkzeug 3.0.1: PYSEC-2026-2043, 2044, 2045, 2046, 1860, 2320, 3417, 4312 (fixed between 3.0.3 and 3.1.9)
  - python-dotenv 1.0.0: PYSEC-2026-2270 (fixed in 1.2.2)
- Expected: no known vulnerabilities in pinned versions, or each one assessed.
- Severity: major. Priority: P2. Category: dependency. Risk: R6.
- Triage: fix later. Upgrading may break the app or tests, so run the full test suite after any change. Exploitability in this app is not assessed yet.

## DR-11 `max_teams` set to NULL crashes `can_register()`
- Summary: if the row's `max_teams` is NULL, `count >= None` raises TypeError.
- Steps: 1. Update `max_teams` to NULL in the database. 2. Open the public registration page.
- Actual: 500. The create form always sets a number (default 16), so users cannot reach this through the app.
- Evidence: RUN (only reproduced by updating the row).
- Severity: minor. Priority: P3. Category: validation. Requirement: FR3. Risk: R1.
- Triage: won't fix, or fix later (low reach). Record the reason either way.

## DR-12 Registration API is CSRF-exempt and no rate limit was seen
- Summary: the `api` blueprint is excluded from CSRF protection, so forged or scripted registrations are possible. No rate limiting was seen in the files read.
- Evidence: READ (`app/__init__.py` exempts `api`, `external_api` and `input_bp`). Not tested.
- Severity: minor (unconfirmed). Priority: P3. Category: access-control. Requirement: FR2. Risk: R8.
- Triage: needs more information. Test with repeated requests before deciding.
