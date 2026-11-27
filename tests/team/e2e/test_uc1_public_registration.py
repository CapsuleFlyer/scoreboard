"""Use case UC1: a visitor registers a team for a tournament (workflow W1, FR1 to FR5).
See docs/use-cases.md for the written use case. Each flow below is one automated test.

Precondition: the tournament exists and registration is open.
Postcondition (main flow): one confirmed team with the entered name exists in that tournament.
Status: written against the templates (READ). Run on your machine before citing any result.
"""
import re

import pytest
from playwright.sync_api import expect


def fill_team(page, name="Robo Team", p1="Ann", p2="Bob", email=None):
    page.fill("input[name=team_name]", name)
    if page.locator("input[name=player1]").count():
        page.fill("input[name=player1]", p1)
        page.fill("input[name=player2]", p2)
    if email is not None:
        page.fill("input[name=email]", email)


def submit(page):
    page.click("#registration-form button[type=submit]")


# ---- main flow --------------------------------------------------------------------------

def test_uc1_main_flow_register_with_the_tournament_code(world, page, shot):
    tid = world.tournament(name="Spring Cup")
    page.goto("/register/")
    page.fill("input[name=code]", "REG001")
    page.click("button[type=submit]")
    expect(page).to_have_url(f"{world.url}/register/tournament/REG001")
    expect(page.locator("h1")).to_contain_text("Spring Cup")
    fill_team(page)
    shot("form")
    submit(page)
    expect(page).to_have_url(re.compile(r"/register/success/REG001/\d+$"))
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    expect(page.locator(".team-item").first).to_contain_text("Robo Team")
    shot("success")
    assert world.teams(tid) == [("Robo Team", True, False)]          # postcondition


# ---- alternative flows ------------------------------------------------------------------

def test_uc1_a1_code_is_accepted_in_lower_case(world, page):
    world.tournament(name="Spring Cup")
    page.goto("/register/")
    page.fill("input[name=code]", "reg001")
    page.click("button[type=submit]")
    expect(page).to_have_url(f"{world.url}/register/tournament/REG001")


def test_uc1_a2_team_waits_for_admin_when_confirmation_is_required(world, page):
    tid = world.tournament(require_confirmation=True)
    page.goto("/register/tournament/REG001")
    fill_team(page)
    submit(page)
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    assert world.teams(tid) == [("Robo Team", False, False)]
    page.goto("/register/tournament/REG001")                          # pending teams are not listed publicly
    expect(page.locator(".team-item")).to_have_count(0)
    expect(page.locator("body")).to_contain_text("No teams registered yet")


@pytest.mark.xfail(strict=True, reason="DR-21: the success message is not shown on the success page, so it is shown on the next page visit instead")
def test_uc1_success_message_does_not_reappear_on_the_next_visit(world, page):
    world.tournament(require_confirmation=True)
    page.goto("/register/tournament/REG001")
    fill_team(page)
    submit(page)
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    page.goto("/register/tournament/REG001")
    expect(page.locator(".alert")).to_have_count(0)


def test_uc1_a3_email_field_appears_and_is_required_when_the_tournament_asks_for_it(world, page):
    tid = world.tournament(require_email=True)
    page.goto("/register/tournament/REG001")
    expect(page.locator("input[name=email]")).to_have_attribute("required", "")
    fill_team(page, email="team@example.com")
    submit(page)
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    assert world.teams(tid) == [("Robo Team", True, False)]


# ---- exception flows --------------------------------------------------------------------

def test_uc1_e1_unknown_code_is_refused(world, page):
    world.tournament()
    page.goto("/register/")
    page.fill("input[name=code]", "NOPE99")
    page.click("button[type=submit]")
    expect(page).to_have_url(f"{world.url}/register/")
    expect(page.locator(".alert")).to_contain_text("Invalid tournament code")


def test_uc1_e2_blank_code_is_refused(world, page):
    world.tournament()
    page.goto("/register/")
    page.fill("input[name=code]", "   ")           # spaces pass the browser's required check
    page.click("button[type=submit]")
    expect(page.locator(".alert")).to_contain_text("Please enter a tournament code")


def test_uc1_e3_duplicate_team_name_is_refused_and_not_stored_twice(world, page):
    tid = world.tournament()
    world.team(tid, "Robo Team")
    page.goto("/register/tournament/REG001")
    fill_team(page, name="Robo Team")
    submit(page)
    expect(page.locator(".alert")).to_contain_text("A team with this name is already registered")
    assert world.teams(tid) == [("Robo Team", True, False)]


def test_uc1_e4_rejected_name_shows_what_to_correct_then_corrected_value_succeeds(world, page, shot):
    tid = world.tournament()
    page.goto("/register/tournament/REG001")
    fill_team(page, name="   ")                    # spaces pass the browser's required check
    submit(page)
    expect(page.locator(".alert")).to_contain_text("Team name is required (max 20 characters)")
    shot("error")
    assert world.teams(tid) == []
    fill_team(page, name="Corrected Team")
    submit(page)
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    assert world.teams(tid) == [("Corrected Team", True, False)]


def test_uc1_e5_closed_registration_hides_the_form(world, page):
    tid = world.tournament(registration_open=False)
    page.goto("/register/tournament/REG001")
    expect(page.locator("#registration-form")).to_have_count(0)
    expect(page.locator("body")).to_contain_text("Registration is closed")
    assert world.teams(tid) == []


def test_uc1_e6_full_tournament_hides_the_form(world, page):
    tid = world.tournament(max_teams=1)
    world.team(tid, "First")
    page.goto("/register/tournament/REG001")
    expect(page.locator("#registration-form")).to_have_count(0)
    expect(page.locator("body")).to_contain_text("Tournament is full")
    assert world.teams(tid) == [("First", True, False)]


# ---- keyboard use (brief section 3) -----------------------------------------------------

def _focused(page):
    return page.evaluate("document.activeElement.name || document.activeElement.type || document.activeElement.tagName")


@pytest.mark.parametrize("fields,order", [
    ({}, ["team_name", "submit"]),
    ({"require_player_names": True}, ["team_name", "player1", "player2", "submit"]),
    ({"require_email": True}, ["team_name", "email", "submit"]),
], ids=["team-name-only", "with-players", "with-email"])
def test_uc1_keyboard_focus_order_and_submit(world, page, fields, order):
    tid = world.tournament(**fields)
    page.goto("/register/tournament/REG001")
    page.focus("input[name=team_name]")
    assert _focused(page) == order[0]
    page.keyboard.type("Keyboard Team")
    typed = {"player1": "Ann", "player2": "Bob", "email": "k@example.com"}
    for name in order[1:]:
        page.keyboard.press("Tab")
        assert _focused(page) == name                 # focus reaches each required field, then the button
        if name in typed:
            page.keyboard.type(typed[name])
    page.keyboard.press("Enter")                      # the keyboard alone submits the form
    expect(page.locator("h1")).to_contain_text("Registration Successful!")
    assert world.teams(tid) == [("Keyboard Team", True, False)]
