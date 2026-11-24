"""Hand-written tests for the JSON registration endpoints (app/blueprints/api.py):
POST /api/register/validate-code and POST /api/register/team.

These cover the business rules that a schema cannot express (rule 2 order of checks, rule 3
confirmation, duplicates, repeated requests, read-back of the shared count). Input-by-input
EP and 3-point BVA are in test_api_generated.py, which is driven by docs/api/openapi.yaml.
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest

from app import db
from app.models import Team, Tournament
from team_support import CODE, make_team, make_tournament, names

VALIDATE = "/api/register/validate-code"
REGISTER = "/api/register/team"


def body(**fields):
    data = {"code": CODE, "team_name": "Alpha", "player1": "Ann", "player2": "Bob"}
    data.update(fields)
    return data


# ---- validate-code ----------------------------------------------------------------------

def test_validate_known_code_returns_public_tournament_info(app, client):
    t = make_tournament(max_teams=4)
    make_team(t, "One")
    r = client.post(VALIDATE, json={"code": f"  {CODE.lower()} "})   # trimmed and upper-cased
    data = r.get_json()
    assert r.status_code == 200
    assert data["valid"] is True and data["can_register"] is True and data["message"] == "OK"
    pub = data["tournament"]
    assert pub["registered_teams"] == 1 and pub["spots_remaining"] == 3 and pub["max_teams"] == 4
    assert "registration_code" not in pub   # to_public_dict must not leak the code


def test_validate_unknown_code(app, client):
    r = client.post(VALIDATE, json={"code": "NOPE99"})
    assert r.status_code == 200
    assert r.get_json() == {"valid": False, "error": "Invalid tournament code"}


def test_validate_missing_code_is_treated_as_unknown(app, client):
    make_tournament()
    assert client.post(VALIDATE, json={}).get_json()["valid"] is False


@pytest.mark.parametrize("fields,message", [
    ({"registration_open": False}, "Registration is closed"),
    ({"status": "in_progress"}, "Tournament has already started"),
])
def test_validate_reports_why_registration_is_not_possible(app, client, fields, message):
    make_tournament(**fields)
    data = client.post(VALIDATE, json={"code": CODE}).get_json()
    assert data["valid"] is True and data["can_register"] is False and data["message"] == message


def test_validate_reports_full_and_spots_remaining_never_negative(app, client):
    t = make_tournament(max_teams=1)
    make_team(t, "One")
    make_team(t, "Two")          # over capacity, possible through manual add races
    data = client.post(VALIDATE, json={"code": CODE}).get_json()
    assert data["can_register"] is False and data["message"] == "Tournament is full"
    assert data["tournament"]["spots_remaining"] == 0   # max(0, ...) branch


# ---- register: success and rule 3 (confirmation) ----------------------------------------

def test_register_success_is_confirmed_by_default(app, client):
    t = make_tournament()
    r = client.post(REGISTER, json=body(email="a@b.co", phone="123"))
    data = r.get_json()
    assert r.status_code == 200 and data["success"] is True
    assert data["confirmed"] is True and data["message"] == "Successfully registered"
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert (team.name, team.email, team.phone, team.is_confirmed) == ("Alpha", "a@b.co", "123", True)
    assert team.registration_ip == "127.0.0.1"
    assert data["team"]["id"] == team.id


def test_register_waits_for_admin_when_confirmation_required(app, client):
    t = make_tournament(require_confirmation=True)
    data = client.post(REGISTER, json=body()).get_json()
    assert data["confirmed"] is False and data["message"] == "Awaiting admin confirmation"
    assert Team.query.filter_by(tournament_id=t.id).one().is_confirmed is False


def test_register_blank_optional_fields_are_stored_as_null(app, client):
    t = make_tournament()
    client.post(REGISTER, json=body(email="  ", phone=""))
    team = Team.query.filter_by(tournament_id=t.id).one()
    assert team.email is None and team.phone is None


# ---- register: rejections, each leaves the database unchanged ---------------------------

def test_register_unknown_code(app, client):
    t = make_tournament()
    r = client.post(REGISTER, json=body(code="NOPE99"))
    assert r.status_code == 400 and r.get_json() == {"success": False, "error": "Invalid tournament code"}
    assert names(t) == []


@pytest.mark.parametrize("fields,message", [
    ({"registration_open": False}, "Registration is closed"),
    ({"status": "ready"}, "Tournament has already started"),
    ({"max_teams": 0}, "Tournament is full"),
])
def test_register_refused_when_rule_2_fails(app, client, fields, message):
    t = make_tournament(**fields)
    r = client.post(REGISTER, json=body())
    assert r.status_code == 400 and r.get_json()["error"] == message
    assert names(t) == []


def test_rule_2_is_checked_before_field_validation(app, client):
    """Order of checks: a closed tournament wins over an invalid team name."""
    make_tournament(registration_open=False)
    r = client.post(REGISTER, json=body(team_name=""))
    assert r.get_json()["error"] == "Registration is closed"


def test_register_requires_email_only_when_the_tournament_says_so(app, client):
    t = make_tournament(require_email=True)
    r = client.post(REGISTER, json=body())
    assert r.status_code == 400 and r.get_json()["error"] == "Email is required for this tournament"
    assert names(t) == []
    assert client.post(REGISTER, json=body(email="a@b.co")).status_code == 200


def test_register_duplicate_name_is_refused_and_not_stored_twice(app, client):
    t = make_tournament()
    assert client.post(REGISTER, json=body()).status_code == 200
    r = client.post(REGISTER, json=body())                      # repeated request
    assert r.status_code == 400 and r.get_json()["error"] == "A team with this name is already registered"
    assert names(t) == ["Alpha"]


def test_register_same_name_in_another_tournament_is_allowed(app, client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    assert client.post(REGISTER, json=body(code="AAA111")).status_code == 200
    assert client.post(REGISTER, json=body(code="BBB222")).status_code == 200
    assert names(t1) == names(t2) == ["Alpha"]


@pytest.mark.xfail(strict=True, reason="DR-04: duplicate check compares names case-sensitively")
def test_register_duplicate_name_ignores_case(app, client):
    t = make_tournament()
    client.post(REGISTER, json=body(team_name="Alpha"))
    r = client.post(REGISTER, json=body(team_name="alpha"))
    assert r.status_code == 400 and names(t) == ["Alpha"]


# ---- shared record: count versus max_teams (read back after success and rejection) ------

def test_shared_count_rises_on_success_and_stays_on_rejection(app, client):
    t = make_tournament(max_teams=2)
    client.post(REGISTER, json=body(team_name="One"))
    client.post(REGISTER, json=body(team_name="Two"))
    assert t.get_registered_team_count() == 2
    r = client.post(REGISTER, json=body(team_name="Three"))
    assert r.status_code == 400 and r.get_json()["error"] == "Tournament is full"
    assert t.get_registered_team_count() == 2
    pub = client.post(VALIDATE, json={"code": CODE}).get_json()["tournament"]
    assert pub["registered_teams"] == 2 and pub["spots_remaining"] == 0


def test_pending_teams_use_capacity(app, client):
    """DR-08 / A4: a pending team counts against max_teams."""
    t = make_tournament(max_teams=1, require_confirmation=True)
    client.post(REGISTER, json=body(team_name="One"))
    r = client.post(REGISTER, json=body(team_name="Two"))
    assert r.status_code == 400 and r.get_json()["error"] == "Tournament is full"
    assert t.get_confirmed_team_count() == 0 and t.get_registered_team_count() == 1


# ---- endpoint weaknesses (reported, not fixed) ------------------------------------------

def test_non_json_request_is_rejected_with_415(app, client):
    make_tournament()
    assert client.post(REGISTER, data="code=REG001").status_code == 415


def test_malformed_json_is_rejected_with_400(app, client):
    make_tournament()
    r = client.post(REGISTER, data="{not json", content_type="application/json")
    assert r.status_code == 400


@pytest.mark.xfail(strict=True, reason="DR-13 (new, unconfirmed): a JSON null body makes data.get raise AttributeError, so the endpoint returns 500 instead of 400")
@pytest.mark.parametrize("url", [VALIDATE, REGISTER])
def test_json_null_body_is_a_client_error_not_a_crash(app, client, url):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    r = client.post(url, data="null", content_type="application/json")
    assert 400 <= r.status_code < 500


def test_endpoints_accept_post_only(app, client):
    assert client.get(REGISTER).status_code == 405
    assert client.get(VALIDATE).status_code == 405
