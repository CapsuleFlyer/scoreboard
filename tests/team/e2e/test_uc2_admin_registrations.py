"""Use case UC2: an admin manages the registrations of a tournament (workflow W2, FR6 to FR12).
See docs/use-cases.md for the written use case. Each flow below is one automated test.

Precondition: the admin has an account and the tournament has registered teams.
Postcondition (main flow): the pending team is confirmed and counts as confirmed everywhere.
Status: written against the templates (READ). Run on your machine before citing any result.
"""
import re

from playwright.sync_api import expect

from e2e_helpers import ADMIN_USER, admin_login


def open_registrations(page, tid):
    page.goto(f"/admin/tournament/{tid}/registrations")


def row(page, team_id):
    return page.locator(f"#team-row-{team_id}")


# ---- main flow --------------------------------------------------------------------------

def test_uc2_main_flow_admin_confirms_a_pending_team(world, page, shot):
    tid = world.tournament(require_confirmation=True)
    team = world.team(tid, "Pending Co", confirmed=False)
    admin_login(page)
    expect(page).to_have_url(f"{world.url}/admin/")
    open_registrations(page, tid)
    expect(row(page, team)).to_contain_text("Pending")
    shot("before")
    page.click(f'#team-row-{team} button[title="Confirm"]')
    expect(row(page, team)).to_contain_text("Confirmed")            # page reloads after the request
    expect(row(page, team).locator('button[title="Confirm"]')).to_have_count(0)
    shot("after")
    assert world.team_row(team) == ("Pending Co", True, False)       # postcondition


# ---- alternative flows ------------------------------------------------------------------

def test_uc2_a1_check_in_can_be_switched_on_and_off(world, page):
    tid = world.tournament()
    team = world.team(tid, "Alpha")
    admin_login(page)
    open_registrations(page, tid)
    page.click(f'#team-row-{team} button[title="Toggle Check-in"]')
    expect(row(page, team)).to_contain_text("Checked In")
    assert world.team_row(team) == ("Alpha", True, True)
    page.click(f'#team-row-{team} button[title="Toggle Check-in"]')
    expect(row(page, team)).not_to_contain_text("Checked In")
    assert world.team_row(team) == ("Alpha", True, False)


def test_uc2_a2_admin_removes_a_team_and_the_slot_is_freed(world, page):
    tid = world.tournament(max_teams=1)
    team = world.team(tid, "Alpha")
    admin_login(page)
    open_registrations(page, tid)
    page.once("dialog", lambda d: d.accept())
    page.click(f'#team-row-{team} button[title="Remove"]')
    expect(row(page, team)).to_have_count(0)
    assert world.team_row(team) is None
    page.goto("/register/tournament/REG001")                          # shared record: capacity is free again
    expect(page.locator("#registration-form")).to_have_count(1)


def test_uc2_a3_admin_adds_a_team_by_hand(world, page):
    tid = world.tournament()
    admin_login(page)
    open_registrations(page, tid)
    page.fill("#add-team-name", "Walkin")
    page.fill("#add-player1", "Ann")
    page.fill("#add-player2", "Bob")
    page.click("#add-team-form button[type=submit]")
    expect(page.locator("tbody")).to_contain_text("Walkin")
    assert world.teams(tid) == [("Walkin", True, False)]


# ---- exception flows --------------------------------------------------------------------

def test_uc2_e1_anonymous_visitor_is_sent_to_the_login_page(world, page):
    tid = world.tournament()
    open_registrations(page, tid)
    expect(page).to_have_url(re.compile(r"/login\?next="))
    assert f"/admin/tournament/{tid}/registrations" in page.url.replace("%2F", "/")


def test_uc2_e2_wrong_password_keeps_the_admin_out(world, page):
    world.tournament()
    admin_login(page, ADMIN_USER, "not-the-password")
    expect(page).to_have_url(f"{world.url}/login")
    expect(page.locator(".alert-error")).to_contain_text("Invalid")


def test_uc2_e3_cancelling_the_remove_dialog_keeps_the_team(world, page):
    tid = world.tournament()
    team = world.team(tid, "Alpha")
    admin_login(page)
    open_registrations(page, tid)
    page.once("dialog", lambda d: d.dismiss())
    page.click(f'#team-row-{team} button[title="Remove"]')
    expect(row(page, team)).to_have_count(1)
    assert world.team_row(team) == ("Alpha", True, False)


def test_uc2_e4_adding_a_duplicate_name_is_refused(world, page):
    tid = world.tournament()
    world.team(tid, "Walkin")
    admin_login(page)
    open_registrations(page, tid)
    page.fill("#add-team-name", "WALKIN")
    page.fill("#add-player1", "Ann")
    page.fill("#add-player2", "Bob")
    with page.expect_event("dialog") as dialog_info:
        page.click("#add-team-form button[type=submit]")
    dialog = dialog_info.value
    message = dialog.message
    dialog.accept()
    assert "already exists" in message
    expect(page.locator("tbody tr")).to_have_count(1)
    assert world.teams(tid) == [("Walkin", True, False)]
