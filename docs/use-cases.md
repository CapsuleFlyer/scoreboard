# Use cases (area 3, DRAFT: read, correct and make them yours)

Derived from `docs/test-basis.md` (FR1 to FR12, business rules 1 to 4). Every flow is one automated test in `tests/team/e2e/`. Postconditions are asserted against the database as well as the page.

## UC1: Register a team (workflow W1)
- **Actor:** visitor (no account). **Requirements:** FR1 to FR5, rules 1 to 3.
- **Precondition:** the tournament exists, registration is open, there is a free slot.
- **Trigger:** the visitor opens `/register/`.
- **Main flow** (`test_uc1_main_flow_register_with_the_tournament_code`)
  1. Visitor enters the tournament code and submits.
  2. System shows the tournament page with its name and the form.
  3. Visitor enters team name and player names and submits.
  4. System stores the team and shows "Registration Successful!" with the team in the list.
- **Postcondition:** one confirmed team with that name exists in the tournament; the registered count is one higher.
- **Alternative flows**
  - A1 the code is typed in lower case: accepted (`..._a1_code_is_accepted_in_lower_case`).
  - A2 the tournament requires confirmation: the team is stored as pending and is not listed publicly (`..._a2_...`).
  - A3 the tournament requires an email: the email field is shown and required (`..._a3_...`).
- **Exception flows**
  - E1 unknown code: error "Invalid tournament code", nothing stored (`..._e1_...`).
  - E2 blank code: "Please enter a tournament code" (`..._e2_...`).
  - E3 duplicate team name: "A team with this name is already registered", no second row (`..._e3_...`).
  - E4 team name rejected (only spaces): the message says what to correct, the corrected name then succeeds (`..._e4_...`).
  - E5 registration closed: the form is not shown (`..._e5_...`).
  - E6 tournament full: the form is not shown (`..._e6_...`).
- **Keyboard flow:** focus moves team name, player 1, player 2, submit, and Enter submits (`test_uc1_keyboard_focus_order_and_submit`).

## UC2: Manage registrations (workflow W2)
- **Actor:** admin. **Requirements:** FR6 to FR12, rules 1 and 3, roles.
- **Precondition:** the admin has an account; the tournament has at least one pending team.
- **Trigger:** the admin logs in and opens the registrations page.
- **Main flow** (`test_uc2_main_flow_admin_confirms_a_pending_team`)
  1. Admin logs in and opens the registrations page of the tournament.
  2. System lists the teams with their status.
  3. Admin presses Confirm on a pending team.
  4. System marks the team Confirmed and removes the Confirm button.
- **Postcondition:** the team is confirmed in the database.
- **Alternative flows**
  - A1 check-in is switched on and off (`..._a1_...`).
  - A2 the admin removes a team: it disappears, the slot is free again on the public page (`..._a2_...`).
  - A3 the admin adds a team by hand (`..._a3_...`).
- **Exception flows**
  - E1 an anonymous visitor is sent to the login page (`..._e1_...`).
  - E2 wrong password: login refused (`..._e2_...`).
  - E3 the admin cancels the remove dialog: the team stays (`..._e3_...`).
  - E4 manual add with an existing name: refused with an error (`..._e4_...`).

## Known behaviour that affects the tests
- Manual add cuts team names to 8 characters (DR-05), so the tests use short names.
- The browser's `required` attribute accepts a value of only spaces; the server then rejects it. E2 and E4 of UC1 rely on that.
