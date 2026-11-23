"""White-box tests for the public registration routes (app/blueprints/register.py).

Covers workflow W1 of docs/test-basis.md: FR1 to FR5 and business rules 1, 3 and 4.
Each test asserts the HTTP result, the flashed message (what the user is told) and the
database state afterwards (the postcondition). CSRF is disabled by the test config, so the
forms can be posted directly.
"""
import pytest

from app import db
from app.models import Team, Tournament

CODE = "REG001"


def make_tournament(**fields):
    values = dict(name="Reg Test", registration_code=CODE, max_teams=16)
    values.update(fields)
    t = Tournament(**values)
    db.session.add(t)
    db.session.commit()
    return t


def team_names(tournament):
    return sorted(t.name for t in Team.query.filter_by(tournament_id=tournament.id).all())


def flashes(client):
    """The flash messages currently waiting in the session, as (category, message)."""
    with client.session_transaction() as sess:
        return [tuple(f) for f in sess.get("_flashes", [])]


def post_team(client, **form):
    data = {"tournament_code": CODE, "team_name": "Alpha"}
    data.update(form)
    return client.post("/register/team", data=data)


def location(response):
    return response.headers["Location"]


# ---- FR1: landing page, code lookup ----------------------------------------------------

def test_index_page_loads(client):
    assert client.get("/register/").status_code == 200


def test_join_with_empty_code_is_refused(client):
    r = client.post("/register/join", data={"code": "   "})
    assert r.status_code == 302 and location(r).endswith("/register/")
    assert ("error", "Please enter a tournament code") in flashes(client)


def test_join_with_unknown_code_is_refused(client):
    r = client.post("/register/join", data={"code": "NOPE99"})
    assert r.status_code == 302 and location(r).endswith("/register/")
    assert ("error", "Invalid tournament code") in flashes(client)


def test_join_with_valid_code_goes_to_the_tournament_page(app, client):
    make_tournament()
    r = client.post("/register/join", data={"code": CODE.lower()})  # lower case is accepted
    assert r.status_code == 302 and location(r).endswith(f"/register/tournament/{CODE}")


def test_tournament_page_with_valid_code(app, client):
    make_tournament()
    assert client.get(f"/register/tournament/{CODE.lower()}").status_code == 200


def test_tournament_page_lists_only_confirmed_teams(app, client):
    t = make_tournament()
    db.session.add(Team(name="Confirmed Co", player1="", player2="", tournament_id=t.id, is_confirmed=True))
    db.session.add(Team(name="Pending Co", player1="", player2="", tournament_id=t.id, is_confirmed=False))
    db.session.commit()
    page = client.get(f"/register/tournament/{CODE}").get_data(as_text=True)
    assert "Confirmed Co" in page
    assert "Pending Co" not in page


def test_tournament_page_with_unknown_code_redirects(client):
    r = client.get("/register/tournament/NOPE99")
    assert r.status_code == 302 and location(r).endswith("/register/")
    assert ("error", "Invalid tournament code") in flashes(client)


# ---- FR2: successful registration, confirmation rule (business rule 3) -----------------

def test_registration_is_confirmed_immediately_by_default(app, client):
    t = make_tournament(require_confirmation=False)
    r = post_team(client, team_name="Alpha")
    team = Team.query.filter_by(tournament_id=t.id, name="Alpha").one()
    assert team.is_confirmed is True
    assert r.status_code == 302 and location(r).endswith(f"/register/success/{CODE}/{team.id}")
    assert ("success", 'Team "Alpha" successfully registered!') in flashes(client)


def test_registration_waits_for_admin_when_confirmation_required(app, client):
    t = make_tournament(require_confirmation=True)
    post_team(client, team_name="Alpha")
    team = Team.query.filter_by(tournament_id=t.id, name="Alpha").one()
    assert team.is_confirmed is False
    assert ("success", 'Team "Alpha" registered! Awaiting admin confirmation.') in flashes(client)


def test_optional_fields_are_stored_and_blank_ones_become_null(app, client):
    t = make_tournament()
    post_team(client, team_name="Alpha", player1="  Ann ", player2="Bob", email="a@b.co", phone="")
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert (team.player1, team.player2, team.email, team.phone) == ("Ann", "Bob", "a@b.co", None)
    assert team.registration_ip == "127.0.0.1"


def test_code_is_case_insensitive_when_registering(app, client):
    t = make_tournament()
    post_team(client, tournament_code=CODE.lower())
    assert team_names(t) == ["Alpha"]


# ---- FR1/FR3: bad code, registration not allowed ---------------------------------------

def test_unknown_tournament_code_is_refused(app, client):
    t = make_tournament()
    r = post_team(client, tournament_code="NOPE99")
    assert r.status_code == 302 and location(r).endswith("/register/")
    assert ("error", "Invalid tournament code") in flashes(client)
    assert team_names(t) == []


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"registration_open": False}, "Registration is closed"),
        ({"status": "in_progress"}, "Tournament has already started"),
        ({"max_teams": 1}, "Tournament is full"),
    ],
    ids=["closed", "started", "full"],
)
def test_registration_refused_when_can_register_is_false(app, client, fields, message):
    t = make_tournament(**fields)
    if fields.get("max_teams") == 1:
        db.session.add(Team(name="Taken", player1="", player2="", tournament_id=t.id))
        db.session.commit()
    r = post_team(client, team_name="Alpha")
    assert r.status_code == 302 and location(r).endswith(f"/register/tournament/{CODE}")
    assert ("error", message) in flashes(client)
    assert "Alpha" not in team_names(t)


# ---- Business rule 1: team name 1-20 characters (boundary value analysis) ---------------

@pytest.mark.parametrize(
    "name, accepted",
    [("", False), ("   ", False), ("A", True), ("A" * 19, True), ("A" * 20, True), ("A" * 21, False)],
    ids=["empty", "spaces_only", "one_char", "19_chars", "20_chars", "21_chars"],
)
def test_team_name_length_boundary(app, client, name, accepted):
    t = make_tournament()
    post_team(client, team_name=name)
    if accepted:
        assert team_names(t) == [name]
    else:
        assert team_names(t) == []
        assert ("error", "Team name is required (max 20 characters)") in flashes(client)


# ---- Business rule 4: conditional fields -----------------------------------------------

@pytest.mark.parametrize(
    "form, message",
    [
        ({"player1": "", "player2": "Bob"}, "Player 1 name is required (max 30 characters)"),
        ({"player1": "A" * 31, "player2": "Bob"}, "Player 1 name is required (max 30 characters)"),
        ({"player1": "Ann", "player2": ""}, "Player 2 name is required (max 30 characters)"),
        ({"player1": "Ann", "player2": "B" * 31}, "Player 2 name is required (max 30 characters)"),
    ],
    ids=["p1_empty", "p1_31_chars", "p2_empty", "p2_31_chars"],
)
def test_player_names_checked_when_required(app, client, form, message):
    t = make_tournament(require_player_names=True)
    post_team(client, **form)
    assert ("error", message) in flashes(client)
    assert team_names(t) == []


@pytest.mark.parametrize("length", [1, 30], ids=["p1_1_char", "p1_30_chars"])
def test_player_name_boundaries_accepted_when_required(app, client, length):
    t = make_tournament(require_player_names=True)
    post_team(client, player1="A" * length, player2="Bob")
    assert team_names(t) == ["Alpha"]


def test_player_names_not_required_by_default(app, client):
    t = make_tournament(require_player_names=False)
    post_team(client)  # no player names at all
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert (team.player1, team.player2) == ("", "")  # stored as empty strings (see DR-06)


def test_email_required_when_tournament_requires_it(app, client):
    t = make_tournament(require_email=True)
    post_team(client, email="")
    assert ("error", "Email is required for this tournament") in flashes(client)
    assert team_names(t) == []


def test_email_accepted_when_tournament_requires_it(app, client):
    t = make_tournament(require_email=True)
    post_team(client, email="a@b.co")
    assert team_names(t) == ["Alpha"]


# ---- FR4: duplicate names --------------------------------------------------------------

def test_duplicate_name_in_same_tournament_is_refused(app, client):
    t = make_tournament()
    post_team(client, team_name="Alpha")
    post_team(client, team_name="Alpha")
    assert team_names(t) == ["Alpha"]  # still exactly one: no duplicate row
    assert ("error", "A team with this name is already registered") in flashes(client)


def test_same_name_is_allowed_in_a_different_tournament(app, client):
    t1 = make_tournament()
    t2 = make_tournament(registration_code="REG002")
    post_team(client, team_name="Alpha")
    post_team(client, tournament_code="REG002", team_name="Alpha")
    assert team_names(t1) == ["Alpha"] and team_names(t2) == ["Alpha"]


@pytest.mark.xfail(strict=True, reason="DR-04: duplicate check on the public form is case-sensitive (assumption A2)")
def test_duplicate_name_differing_only_in_case_is_refused(app, client):
    t = make_tournament()
    post_team(client, team_name="Alpha")
    post_team(client, team_name="alpha")
    assert team_names(t) == ["Alpha"]


# ---- Success page ----------------------------------------------------------------------

def test_success_page_for_a_registered_team(app, client):
    t = make_tournament()
    post_team(client)
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert client.get(f"/register/success/{CODE}/{team.id}").status_code == 200


def test_success_page_with_unknown_team_redirects(app, client):
    make_tournament()
    r = client.get(f"/register/success/{CODE}/9999")
    assert r.status_code == 302 and location(r).endswith("/register/")


def test_success_page_with_unknown_code_redirects(client):
    r = client.get("/register/success/NOPE99/1")
    assert r.status_code == 302 and location(r).endswith("/register/")
