"""Whole-app tests: the token-authenticated external API (app/blueprints/external_api.py, /ext/v1).
Status: written against the source (READ). Run on your machine before citing any result.

New suspected defects, kept as strict xfail so a run confirms or refutes them:
  DR-16  a token with an expires_at date makes validate_token compare a naive and an aware
         datetime (same root cause as DR-03), so the request crashes
  DR-18  a token scoped to one tournament is never checked against the tournament in the URL
  DR-19  a non-numeric score makes int() raise, so the API answers 500 instead of 400
"""
from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.models import APIToken, DisplayState, Match
from team_support import make_tournament
from team_support_more import bearer, make_match, make_teams, make_token

BASE = "/ext/v1"


def setup_match(**fields):
    t = make_tournament()
    a, b = make_teams(t, 2)
    return t, a, b, make_match(t, team1=a, team2=b, **fields)


# ---- public endpoints and token checks --------------------------------------------------

def test_health_and_scopes_need_no_token(app, client):
    assert client.get(f"{BASE}/health").get_json()["status"] == "ok"
    data = client.get(f"{BASE}/scopes").get_json()
    assert data["scopes"] == APIToken.SCOPES and "tournament:read" in data["description"]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Token abc"}, {"Authorization": "bearer abc"}])
def test_missing_or_malformed_authorization_header_is_401(app, client, headers):
    r = client.get(f"{BASE}/tournament/1", headers=headers)
    assert r.status_code == 401 and "hint" in r.get_json()


def test_unknown_inactive_token_is_401(app, client):
    _, raw = make_token(active=False)
    for headers in (bearer("not-a-token"), bearer(raw)):
        r = client.get(f"{BASE}/tournament/1", headers=headers)
        assert r.status_code == 401 and r.get_json() == {"error": "Invalid or expired token"}


def test_token_without_the_scope_is_403_and_lists_its_permissions(app, client):
    t = make_tournament()
    _, raw = make_token(permissions=["team:read"])
    r = client.get(f"{BASE}/tournament/{t.id}", headers=bearer(raw))
    assert r.status_code == 403
    assert r.get_json()["error"] == "Token lacks required permission: tournament:read"
    assert r.get_json()["your_permissions"] == ["team:read"]


def test_valid_token_updates_its_usage_counters(app, client):
    t = make_tournament()
    token, raw = make_token()
    client.get(f"{BASE}/tournament/{t.id}", headers=bearer(raw))
    client.get(f"{BASE}/tournament/{t.id}", headers=bearer(raw))
    db.session.expire_all()
    token = db.session.get(APIToken, token.id)
    assert token.request_count == 2 and token.last_used is not None


@pytest.mark.xfail(strict=True, reason="DR-16: token expiry compares a naive and an aware datetime")
@pytest.mark.parametrize("delta,status", [(timedelta(days=1), 200), (timedelta(days=-1), 401)])
def test_token_expiry_is_honoured(app, client, delta, status):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    t = make_tournament()
    _, raw = make_token(expires_at=datetime.now(timezone.utc) + delta)
    assert client.get(f"{BASE}/tournament/{t.id}", headers=bearer(raw)).status_code == status


@pytest.mark.xfail(strict=True, reason="DR-18: tournament_id on a token is never enforced")
def test_token_scoped_to_one_tournament_cannot_read_another(app, client):
    mine = make_tournament(registration_code="AAA111")
    other = make_tournament(registration_code="BBB222")
    _, raw = make_token(tournament_id=mine.id)
    assert client.get(f"{BASE}/tournament/{other.id}", headers=bearer(raw)).status_code == 403


# ---- read endpoints ---------------------------------------------------------------------

def test_get_tournament_and_team_count(app, client):
    t = make_tournament()
    make_teams(t, 3)
    _, raw = make_token()
    data = client.get(f"{BASE}/tournament/{t.id}", headers=bearer(raw)).get_json()
    assert data["tournament"]["id"] == t.id and data["team_count"] == 3


def test_missing_records_are_404(app, client):
    _, raw = make_token()
    for path in ("/tournament/9999", "/tournament/9999/current", "/tournament/9999/teams", "/match/9999"):
        r = client.get(BASE + path, headers=bearer(raw))
        assert r.status_code == 404 and r.get_json()["error"].endswith("not found")


def test_current_match_present_and_absent(app, client):
    t, a, b, m = setup_match()
    _, raw = make_token()
    none = client.get(f"{BASE}/tournament/{t.id}/current", headers=bearer(raw)).get_json()
    assert none == {"current_match": None, "message": "No active match"}
    m.is_current = True
    db.session.commit()
    data = client.get(f"{BASE}/tournament/{t.id}/current", headers=bearer(raw)).get_json()
    assert data["current_match"]["id"] == m.id and data["team1"]["id"] == a.id and data["team2"]["id"] == b.id


def test_current_match_with_missing_teams(app, client):
    t = make_tournament()
    make_match(t, is_current=True)
    _, raw = make_token()
    data = client.get(f"{BASE}/tournament/{t.id}/current", headers=bearer(raw)).get_json()
    assert data["team1"] is None and data["team2"] is None


def test_tournament_teams_and_match_details(app, client):
    t, a, b, m = setup_match()
    _, raw = make_token()
    teams = client.get(f"{BASE}/tournament/{t.id}/teams", headers=bearer(raw)).get_json()
    assert teams["tournament_id"] == t.id and len(teams["teams"]) == 2
    data = client.get(f"{BASE}/match/{m.id}", headers=bearer(raw)).get_json()
    assert data["match"]["id"] == m.id and data["team1"]["id"] == a.id


def test_match_details_with_missing_teams(app, client):
    t = make_tournament()
    m = make_match(t)
    _, raw = make_token()
    data = client.get(f"{BASE}/match/{m.id}", headers=bearer(raw)).get_json()
    assert data["team1"] is None and data["team2"] is None


# ---- scoring ----------------------------------------------------------------------------

def test_update_score_converts_values_to_integers(app, client):
    t, a, b, m = setup_match()
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m.id}/score", json={"team1_score": "5", "team2_score": 3}, headers=bearer(raw))
    assert r.get_json()["success"] is True
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (5, 3)
    client.post(f"{BASE}/match/{m.id}/score", json={}, headers=bearer(raw))     # no keys: nothing changes
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (5, 3)


def test_update_score_rejections(app, client):
    t, a, b, m = setup_match(is_completed=True)
    _, raw = make_token()
    assert client.post(f"{BASE}/match/9999/score", json={}, headers=bearer(raw)).status_code == 404
    r = client.post(f"{BASE}/match/{m.id}/score", json={"team1_score": 1}, headers=bearer(raw))
    assert r.status_code == 400 and r.get_json()["error"] == "Match is already completed"
    _, only_read = make_token(permissions=["match:read"])
    assert client.post(f"{BASE}/match/{m.id}/score", json={}, headers=bearer(only_read)).status_code == 403


@pytest.mark.xfail(strict=True, reason="DR-19 (READ): int() on a non-numeric score raises ValueError, so the API answers 500")
def test_update_score_with_a_non_numeric_value_is_a_client_error(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    t, a, b, m = setup_match()
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m.id}/score", json={"team1_score": "abc"}, headers=bearer(raw))
    assert r.status_code == 400


def test_add_point(app, client):
    t, a, b, m = setup_match()
    _, raw = make_token()
    assert client.post(f"{BASE}/match/{m.id}/add-point", json={"team": 1}, headers=bearer(raw)).get_json() == {
        "success": True, "team1_score": 1, "team2_score": 0}
    assert client.post(f"{BASE}/match/{m.id}/add-point", json={"team": 2}, headers=bearer(raw)).get_json() == {
        "success": True, "team1_score": 1, "team2_score": 1}


@pytest.mark.parametrize("body", [{"team": 3}, {"team": 0}, {"team": "1"}, {}])
def test_add_point_needs_team_one_or_two(app, client, body):
    t, a, b, m = setup_match()
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m.id}/add-point", json=body, headers=bearer(raw))
    assert r.status_code == 400 and r.get_json()["error"] == "Invalid team, must be 1 or 2"
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (0, 0)


def test_add_point_on_missing_or_completed_match(app, client):
    t, a, b, m = setup_match(is_completed=True)
    _, raw = make_token()
    assert client.post(f"{BASE}/match/9999/add-point", json={"team": 1}, headers=bearer(raw)).status_code == 404
    assert client.post(f"{BASE}/match/{m.id}/add-point", json={"team": 1}, headers=bearer(raw)).status_code == 400


# ---- winners ----------------------------------------------------------------------------

@pytest.mark.parametrize("score1,score2,body,winner", [
    (3, 1, {}, "a"), (1, 3, {}, "b"), (2, 2, {"force_team": 1}, "a"), (2, 2, {"force_team": 2}, "b"),
    (0, 9, {"force_team": 1}, "a"),
])
def test_set_winner(app, client, score1, score2, body, winner):
    t, a, b, m = setup_match(score1=score1, score2=score2, is_current=True)
    _, raw = make_token()
    data = client.post(f"{BASE}/match/{m.id}/set-winner", json=body, headers=bearer(raw)).get_json()
    expected = a if winner == "a" else b
    assert data["success"] is True and data["winner_id"] == expected.id and data["winner_name"] == expected.name
    db.session.expire_all()
    assert (m.winner_id, m.is_completed, m.is_current) == (expected.id, True, False)


def test_set_winner_refuses_a_tie_and_a_completed_match(app, client):
    t, a, b, m = setup_match(score1=2, score2=2)
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m.id}/set-winner", json={}, headers=bearer(raw))
    assert r.status_code == 400 and "force_team" in r.get_json()["hint"]
    m.is_completed = True
    db.session.commit()
    assert client.post(f"{BASE}/match/{m.id}/set-winner", json={}, headers=bearer(raw)).status_code == 400
    assert client.post(f"{BASE}/match/9999/set-winner", json={}, headers=bearer(raw)).status_code == 404


def test_set_winner_moves_the_winner_to_the_next_match(app, client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    final = make_match(t, 2, 1)
    m1 = make_match(t, 1, 1, a, b, 5, 1, next_match_id=final.id, is_current=True)
    m2 = make_match(t, 1, 2, c, d, 0, 4, next_match_id=final.id)
    _, raw = make_token()
    client.post(f"{BASE}/match/{m1.id}/set-winner", json={}, headers=bearer(raw))
    db.session.expire_all()
    assert final.team1_id == a.id and m2.is_current is True
    client.post(f"{BASE}/match/{m2.id}/set-winner", json={}, headers=bearer(raw))
    db.session.expire_all()
    assert final.team2_id == d.id and final.is_current is True


def test_complete_with_a_winner(app, client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    final = make_match(t, 2, 1)
    m1 = make_match(t, 1, 1, a, b, next_match_id=final.id)
    make_match(t, 1, 2, c, d, next_match_id=final.id)
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m1.id}/complete", json={"winner_id": b.id}, headers=bearer(raw))
    assert r.get_json()["success"] is True
    db.session.expire_all()
    assert (m1.winner_id, m1.is_completed, final.team1_id) == (b.id, True, b.id)
    m3 = make_match(t, 3, 1, c, d, next_match_id=final.id)
    client.post(f"{BASE}/match/{m3.id}/complete", json={"winner_id": c.id}, headers=bearer(raw))
    db.session.expire_all()
    assert final.team2_id == c.id


@pytest.mark.parametrize("body,error", [
    ({}, "winner_id is required"),
    ({"winner_id": 99999}, "winner_id must be one of the teams in this match"),
])
def test_complete_rejections(app, client, body, error):
    t, a, b, m = setup_match()
    _, raw = make_token()
    r = client.post(f"{BASE}/match/{m.id}/complete", json=body, headers=bearer(raw))
    assert r.status_code == 400 and r.get_json()["error"] == error
    db.session.expire_all()
    assert m.is_completed is False


def test_complete_on_missing_or_completed_match(app, client):
    t, a, b, m = setup_match(is_completed=True)
    _, raw = make_token()
    assert client.post(f"{BASE}/match/9999/complete", json={"winner_id": 1}, headers=bearer(raw)).status_code == 404
    assert client.post(f"{BASE}/match/{m.id}/complete", json={"winner_id": a.id}, headers=bearer(raw)).status_code == 400


# ---- display and timer ------------------------------------------------------------------

def test_display_mode_creates_and_updates_the_state(app, client):
    t = make_tournament()
    _, raw = make_token()
    data = client.post(f"{BASE}/display/mode", headers=bearer(raw), json={
        "mode": "winner", "tournament_id": t.id, "custom_message": "Well played", "winner_team_id": 3}).get_json()
    assert data["success"] is True and data["display_state"]["mode"] == "winner"
    assert data["display_state"]["custom_message"] == "Well played"
    client.post(f"{BASE}/display/mode", headers=bearer(raw), json={})            # no keys: unchanged
    assert DisplayState.query.count() == 1 and DisplayState.query.one().mode == "winner"


def test_countdown_start(app, client):
    t = make_tournament(timer_duration=120)
    _, raw = make_token()
    assert client.post(f"{BASE}/countdown/start", json={"tournament_id": t.id}, headers=bearer(raw)).get_json() == {
        "success": True, "duration": 120}
    assert client.post(f"{BASE}/countdown/start", json={"tournament_id": t.id, "duration": 30},
                       headers=bearer(raw)).get_json()["duration"] == 30


def test_countdown_start_rejections(app, client):
    _, raw = make_token()
    r = client.post(f"{BASE}/countdown/start", json={}, headers=bearer(raw))
    assert r.status_code == 400 and r.get_json()["error"] == "tournament_id is required"
    r = client.post(f"{BASE}/countdown/start", json={"tournament_id": 9999}, headers=bearer(raw))
    assert r.status_code == 404 and r.get_json()["error"] == "Tournament not found"
