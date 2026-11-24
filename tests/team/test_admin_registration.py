"""Tests for workflow W2, admin registration management (app/blueprints/admin.py).

Covers FR6 to FR12 and business rules 1 and 3 of docs/test-basis.md. Each test asserts the
HTTP result, the JSON the admin UI receives and the database state afterwards.
Status: written against the source (READ). Run on your machine before citing any result.

Known defects are documented with strict xfail so the suite stays green and flips to a
failure (XPASS) the day the defect is fixed:
  DR-05 admin add truncates names to 8 and 10 characters
  DR-07 admin add ignores closed or started tournaments
  DR-02 a missing team or tournament returns 500 instead of 404
"""
import pytest

from app import db
from app.models import Team, Tournament
from team_support import make_team, make_tournament, names, reload_team

GOOD = {"name": "Robots", "player1": "Ann", "player2": "Bob"}


def add(client, tid, **body):
    data = dict(GOOD)
    data.update(body)
    return client.post(f"/admin/tournament/{tid}/team/add", json=data)


# ---- FR6 / roles: anonymous visitor is sent to the login page ---------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/admin/tournament/{t}/registrations"),
    ("post", "/admin/tournament/{t}/team/{m}/confirm"),
    ("post", "/admin/tournament/{t}/team/{m}/reject"),
    ("post", "/admin/tournament/{t}/team/{m}/checkin"),
    ("post", "/admin/tournament/{t}/team/add"),
    ("post", "/admin/tournament/{t}/registration/toggle"),
])
def test_anonymous_is_redirected_to_login_and_nothing_changes(app, client, method, path):
    t = make_tournament()
    team = make_team(t, confirmed=False)
    r = getattr(client, method)(path.format(t=t.id, m=team.id))
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert "next=" in r.headers["Location"]
    assert reload_team(team.id).is_confirmed is False
    assert names(t) == ["Alpha"]
    assert db.session.get(Tournament, t.id).registration_open is True


# ---- registrations page -----------------------------------------------------------------

def test_registrations_page_lists_pending_and_confirmed_teams(app, authenticated_client):
    t = make_tournament(name="Page Cup")
    make_team(t, "Confirmed Co", confirmed=True)
    make_team(t, "Pending Co", confirmed=False)
    r = authenticated_client.get(f"/admin/tournament/{t.id}/registrations")
    page = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Page Cup" in page and "Confirmed Co" in page and "Pending Co" in page


@pytest.mark.xfail(strict=True, reason="DR-02: the 404 page calls url_for('ui.index'), so a missing tournament is not a clean 404")
def test_registrations_page_for_missing_tournament_is_404(app, authenticated_client):
    assert authenticated_client.get("/admin/tournament/9999/registrations").status_code == 404


# ---- FR7: confirm (state change pending -> confirmed) -----------------------------------

def test_confirm_pending_team(app, authenticated_client):
    t = make_tournament()
    team = make_team(t, confirmed=False)
    r = authenticated_client.post(f"/admin/tournament/{t.id}/team/{team.id}/confirm")
    body = r.get_json()
    assert r.status_code == 200 and body["success"] is True
    assert body["team"]["id"] == team.id and body["team"]["is_confirmed"] is True
    assert reload_team(team.id).is_confirmed is True


def test_confirm_is_idempotent_on_a_confirmed_team(app, authenticated_client):
    t = make_tournament()
    team = make_team(t, confirmed=True)
    r = authenticated_client.post(f"/admin/tournament/{t.id}/team/{team.id}/confirm")
    assert r.status_code == 200 and r.get_json()["success"] is True
    assert reload_team(team.id).is_confirmed is True
    assert names(t) == ["Alpha"]  # no duplicate row


def test_confirm_team_from_another_tournament_is_refused(app, authenticated_client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    team = make_team(t2, confirmed=False)
    r = authenticated_client.post(f"/admin/tournament/{t1.id}/team/{team.id}/confirm")
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": "Team not in this tournament"}
    assert reload_team(team.id).is_confirmed is False


@pytest.mark.xfail(strict=True, reason="DR-02: get_or_404 renders the broken 404 page")
def test_confirm_missing_team_is_404(app, authenticated_client):
    t = make_tournament()
    assert authenticated_client.post(f"/admin/tournament/{t.id}/team/9999/confirm").status_code == 404


# ---- FR8: reject deletes the row and frees the slot -------------------------------------

def test_reject_deletes_team_and_frees_the_slot(app, authenticated_client):
    t = make_tournament(max_teams=1)
    team = make_team(t, confirmed=False)
    assert t.can_register() == (False, "Tournament is full")
    r = authenticated_client.post(f"/admin/tournament/{t.id}/team/{team.id}/reject")
    assert r.status_code == 200 and r.get_json() == {"success": True}
    assert reload_team(team.id) is None
    assert t.get_registered_team_count() == 0
    assert t.can_register() == (True, "OK")  # shared record read back: capacity is free again


def test_reject_works_on_a_confirmed_team_too(app, authenticated_client):
    t = make_tournament()
    team = make_team(t, confirmed=True)
    assert authenticated_client.post(f"/admin/tournament/{t.id}/team/{team.id}/reject").status_code == 200
    assert names(t) == []


def test_reject_team_from_another_tournament_is_refused(app, authenticated_client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    team = make_team(t2)
    r = authenticated_client.post(f"/admin/tournament/{t1.id}/team/{team.id}/reject")
    assert r.status_code == 400 and r.get_json()["error"] == "Team not in this tournament"
    assert reload_team(team.id) is not None


def test_reject_twice_second_call_cannot_find_the_team(app, authenticated_client):
    """Repeated request: the first call deletes, the second must not succeed or create rows."""
    t = make_tournament()
    team = make_team(t)
    url = f"/admin/tournament/{t.id}/team/{team.id}/reject"
    assert authenticated_client.post(url).status_code == 200
    app.config["PROPAGATE_EXCEPTIONS"] = False  # DR-02 would otherwise raise inside the client
    assert authenticated_client.post(url).status_code in (404, 500)
    assert names(t) == []


# ---- FR9: check-in is an independent toggle ---------------------------------------------

def test_checkin_toggles_on_then_off(app, authenticated_client):
    t = make_tournament()
    team = make_team(t, confirmed=True)
    url = f"/admin/tournament/{t.id}/team/{team.id}/checkin"
    r1 = authenticated_client.post(url)
    assert r1.status_code == 200 and r1.get_json() == {"success": True, "checked_in": True}
    assert reload_team(team.id).is_checked_in is True
    r2 = authenticated_client.post(url)
    assert r2.get_json() == {"success": True, "checked_in": False}
    assert reload_team(team.id).is_checked_in is False


def test_checkin_does_not_change_confirmation(app, authenticated_client):
    """Documents N3: check-in works on a pending team and leaves is_confirmed alone."""
    t = make_tournament()
    team = make_team(t, confirmed=False)
    authenticated_client.post(f"/admin/tournament/{t.id}/team/{team.id}/checkin")
    row = reload_team(team.id)
    assert row.is_checked_in is True and row.is_confirmed is False


def test_checkin_team_from_another_tournament_is_refused(app, authenticated_client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    team = make_team(t2)
    r = authenticated_client.post(f"/admin/tournament/{t1.id}/team/{team.id}/checkin")
    assert r.status_code == 400 and r.get_json()["success"] is False
    assert reload_team(team.id).is_checked_in is False


# ---- FR10: manual add -------------------------------------------------------------------

def test_manual_add_creates_a_confirmed_team(app, authenticated_client):
    t = make_tournament()
    r = add(authenticated_client, t.id)
    body = r.get_json()
    assert r.status_code == 200 and body["success"] is True
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert (team.name, team.player1, team.player2, team.is_confirmed) == ("Robots", "Ann", "Bob", True)
    assert body["team"]["id"] == team.id


@pytest.mark.parametrize("missing", ["name", "player1", "player2"])
def test_manual_add_requires_all_three_fields(app, authenticated_client, missing):
    t = make_tournament()
    r = add(authenticated_client, t.id, **{missing: "   "})
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": "All fields are required"}
    assert names(t) == []


def test_manual_add_refuses_duplicate_name_ignoring_case(app, authenticated_client):
    t = make_tournament()
    make_team(t, "Robots")
    r = add(authenticated_client, t.id, name="ROBOTS")
    assert r.status_code == 400 and "already exists" in r.get_json()["error"]
    assert names(t) == ["Robots"]


def test_manual_add_allows_same_name_in_another_tournament(app, authenticated_client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    make_team(t1, "Robots")
    assert add(authenticated_client, t2.id).status_code == 200
    assert names(t2) == ["Robots"]


def test_manual_add_refuses_when_full_then_succeeds_after_a_slot_is_freed(app, authenticated_client):
    t = make_tournament(max_teams=1)
    first = make_team(t, "First")
    r = add(authenticated_client, t.id, name="Second")
    assert r.status_code == 400 and r.get_json()["error"] == "Tournament is full"
    assert names(t) == ["First"]  # read back after the rejection
    authenticated_client.post(f"/admin/tournament/{t.id}/team/{first.id}/reject")
    assert add(authenticated_client, t.id, name="Second").status_code == 200
    assert names(t) == ["Second"]


def test_manual_add_boundary_count_one_below_max_is_accepted(app, authenticated_client):
    t = make_tournament(max_teams=2)
    make_team(t, "First")                      # count 1 = max - 1
    assert add(authenticated_client, t.id, name="Second").status_code == 200
    assert add(authenticated_client, t.id, name="Third").status_code == 400   # count 2 = max
    assert t.get_registered_team_count() == 2


def test_manual_add_strips_unsafe_characters(app, authenticated_client):
    t = make_tournament()
    r = add(authenticated_client, t.id, name="a<b>c")
    assert r.status_code == 200
    assert names(t) == ["abc"]  # '<' and '>' are removed by sanitize_team_name


@pytest.mark.xfail(strict=True, reason="DR-05: sanitize_team_name cuts names to 8 characters and player names to 10")
def test_manual_add_keeps_a_20_character_team_name(app, authenticated_client):
    t = make_tournament()
    add(authenticated_client, t.id, name="A" * 20, player1="P" * 30)
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert len(team.name) == 20 and len(team.player1) == 30


def test_manual_add_current_truncation_is_8_and_10_characters(app, authenticated_client):
    """Pins today's behaviour so a fix of DR-05 is noticed (this test then fails on purpose)."""
    t = make_tournament()
    add(authenticated_client, t.id, name="Robotics Club", player1="Bartholomew Jones")
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert (team.name, team.player1) == ("Robotics", "Bartholome")


@pytest.mark.xfail(strict=True, reason="DR-07: manual add does not call can_register(), so it works when registration is closed")
def test_manual_add_is_refused_when_registration_is_closed(app, authenticated_client):
    t = make_tournament(registration_open=False)
    r = add(authenticated_client, t.id)
    assert r.status_code == 400 and names(t) == []


@pytest.mark.xfail(strict=True, reason="DR-07: manual add ignores tournament status")
def test_manual_add_is_refused_after_the_tournament_started(app, authenticated_client):
    t = make_tournament(status="in_progress")
    r = add(authenticated_client, t.id)
    assert r.status_code == 400 and names(t) == []


# ---- FR12: registration toggle (state change open <-> closed) ---------------------------

def test_toggle_closes_then_reopens_and_public_rule_follows(app, authenticated_client):
    t = make_tournament()
    url = f"/admin/tournament/{t.id}/registration/toggle"
    r1 = authenticated_client.post(url)
    assert r1.get_json() == {"success": True, "registration_open": False}
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).can_register() == (False, "Registration is closed")
    r2 = authenticated_client.post(url)
    assert r2.get_json() == {"success": True, "registration_open": True}
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).can_register() == (True, "OK")
