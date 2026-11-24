"""Tests added to kill the 15 surviving mutants of the first mutation run (see docs/mutation-analysis.md).

Three groups, one per cause:
  weak assertion  earlier tests checked the status code or one JSON key, so a mutated key or
                  message text went unnoticed. These tests compare the WHOLE response body.
  missing test    no test sent two invalid fields at once, so swapping two guard clauses was
                  invisible. These tests make the order of the checks observable.
  missing test    nothing listened to the Socket.IO event the endpoint emits after success.
Status: written against the source (READ). Run, then rerun scripts/mutate_rules.py to confirm.
"""
import pytest

from app import socketio
from team_support import CODE, make_tournament

REGISTER = "/api/register/team"

NAME_MSG = "Team name is required (max 20 characters)"
P1_MSG = "Player 1 name is required (max 30 characters)"
P2_MSG = "Player 2 name is required (max 30 characters)"


def body(**fields):
    data = {"code": CODE, "team_name": "Alpha", "player1": "Ann", "player2": "Bob"}
    data.update(fields)
    return data


# ---- weak assertion: exact JSON of every rejection --------------------------------------

def test_rule_2_rejection_has_the_exact_body(app, client):
    make_tournament(registration_open=False)
    r = client.post(REGISTER, json=body())
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": "Registration is closed"}


@pytest.mark.parametrize("field,value,message", [
    ("team_name", "", NAME_MSG),
    ("team_name", "A" * 21, NAME_MSG),
    ("player1", "", P1_MSG),
    ("player1", "P" * 31, P1_MSG),
    ("player2", "", P2_MSG),
    ("player2", "P" * 31, P2_MSG),
])
def test_field_rejection_names_the_field_to_correct(app, client, field, value, message):
    make_tournament()
    r = client.post(REGISTER, json=body(**{field: value}))
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": message}


def test_missing_email_rejection_has_the_exact_body(app, client):
    make_tournament(require_email=True)
    r = client.post(REGISTER, json=body())
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": "Email is required for this tournament"}


def test_duplicate_rejection_has_the_exact_body(app, client):
    make_tournament()
    client.post(REGISTER, json=body())
    r = client.post(REGISTER, json=body())
    assert r.status_code == 400
    assert r.get_json() == {"success": False, "error": "A team with this name is already registered"}


# ---- missing test: order of the guard clauses -------------------------------------------

def test_team_name_is_reported_before_player1(app, client):
    make_tournament()
    r = client.post(REGISTER, json=body(team_name="", player1=""))
    assert r.get_json()["error"] == NAME_MSG


def test_player1_is_reported_before_player2(app, client):
    make_tournament()
    r = client.post(REGISTER, json=body(player1="", player2=""))
    assert r.get_json()["error"] == P1_MSG


def test_player2_is_reported_before_missing_email(app, client):
    make_tournament(require_email=True)
    r = client.post(REGISTER, json=body(player2=""))      # email is also missing
    assert r.get_json()["error"] == P2_MSG


# ---- missing test: the Socket.IO event after a successful registration -------------------

def test_success_emits_team_registered_with_tournament_and_team(app, client):
    t = make_tournament()
    listener = socketio.test_client(app)
    listener.get_received()                                # drop anything sent on connect
    assert client.post(REGISTER, json=body()).status_code == 200
    events = [e for e in listener.get_received() if e["name"] == "team_registered"]
    listener.disconnect()
    assert len(events) == 1
    payload = events[0]["args"][0]
    assert payload["tournament_id"] == t.id
    assert payload["team"]["name"] == "Alpha"


def test_rejected_registration_emits_nothing(app, client):
    make_tournament(registration_open=False)
    listener = socketio.test_client(app)
    listener.get_received()
    client.post(REGISTER, json=body())
    names = [e["name"] for e in listener.get_received()]
    listener.disconnect()
    assert "team_registered" not in names
