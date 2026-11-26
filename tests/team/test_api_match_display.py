"""Whole-app tests: app/blueprints/api.py outside registration (match scoring, bracket, display,
themes, TV pairing and control, bracket self-test).
Status: written against the source (READ). Run on your machine before citing any result.

New suspected defects, kept as strict xfail so a run confirms or refutes them:
  DR-15  api.py uses sanitize_message but never imports it: any request with custom_message crashes
  DR-17  /api/tournament/<id>/timer and /api/display/mode change state with no login
"""
from datetime import datetime, timedelta

import pytest

from app import db
from app.models import DisplayState, Match, Team, Tournament, TVSession
from team_support import make_tournament
from team_support_more import make_match, make_teams, make_tv


def setup_match(**fields):
    t = make_tournament()
    a, b = make_teams(t, 2)
    return t, a, b, make_match(t, team1=a, team2=b, **fields)


# ---- access ----------------------------------------------------------------------------

@pytest.mark.parametrize("method,path,status", [
    ("post", "/api/match/1/score", 401), ("post", "/api/match/1/swap-teams", 401),
    ("post", "/api/match/1/complete", 401), ("post", "/api/match/1/set-current", 401),
    ("post", "/api/test/generate-brackets", 401),
    ("get", "/api/match/1", 401), ("get", "/api/tournament/1/bracket", 401),
    ("get", "/api/tournament/1/next-match", 401), ("get", "/api/tournament/1/stats", 401),
    ("get", "/api/tournament/1/teams", 401),
])
def test_protected_api_routes_answer_401_to_anonymous_callers(app, client, method, path, status):
    assert getattr(client, method)(path, json={}).status_code == status


@pytest.mark.parametrize("method,path", [
    ("post", "/api/display/theme"), ("post", "/api/tv/pair"), ("post", "/api/tv/pair-all"),
    ("post", "/api/tv/unpair"), ("post", "/api/tv/validate"), ("get", "/api/tv/sessions"),
    ("post", "/api/tv/ABC234/control"),
])
def test_login_protected_api_routes_redirect_anonymous_callers(app, client, method, path):
    r = getattr(client, method)(path, json={})
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ---- match scoring ----------------------------------------------------------------------

def test_get_match_for_admin_and_for_an_active_tv(app, authenticated_client, client):
    t, a, b, m = setup_match()
    assert authenticated_client.get(f"/api/match/{m.id}").get_json()["team1"]["id"] == a.id
    tv = make_tv("ABC234")
    other = app.test_client()
    with other.session_transaction() as s:
        s["tv_session_id"] = tv.id
    assert other.get(f"/api/match/{m.id}").status_code == 200


def test_update_score_sets_only_the_keys_sent(app, authenticated_client):
    t, a, b, m = setup_match(score1=1, score2=1)
    data = authenticated_client.post(f"/api/match/{m.id}/score", json={"team1_score": 5}).get_json()
    assert (data["team1_score"], data["team2_score"]) == (5, 1)
    data = authenticated_client.post(f"/api/match/{m.id}/score", json={"team2_score": 4}).get_json()
    assert (data["team1_score"], data["team2_score"]) == (5, 4)


def test_swap_teams_exchanges_ids_and_scores(app, authenticated_client):
    t, a, b, m = setup_match(score1=3, score2=1)
    authenticated_client.post(f"/api/match/{m.id}/swap-teams")
    db.session.expire_all()
    assert (m.team1_id, m.team2_id, m.team1_score, m.team2_score) == (b.id, a.id, 1, 3)


def test_complete_match_advances_the_winner_and_starts_the_next_match(app, authenticated_client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    final = make_match(t, 2, 1)
    m1 = make_match(t, 1, 1, a, b, next_match_id=final.id, is_current=True)
    m2 = make_match(t, 1, 2, c, d, next_match_id=final.id)
    authenticated_client.post(f"/api/match/{m1.id}/complete", json={"winner_id": a.id})
    db.session.expire_all()
    assert (m1.winner_id, m1.is_completed, m1.is_current) == (a.id, True, False)
    assert final.team1_id == a.id and final.team2_id is None
    assert m2.is_current is True                              # next playable match starts
    data = authenticated_client.post(f"/api/match/{m2.id}/complete", json={"winner_id": d.id}).get_json()
    db.session.expire_all()
    assert final.team2_id == d.id and final.is_current is True and data["winner"]["id"] == d.id


def test_complete_match_without_winner_or_next_match(app, authenticated_client):
    t, a, b, m = setup_match()
    data = authenticated_client.post(f"/api/match/{m.id}/complete", json={}).get_json()
    assert data["is_completed"] is True and data["winner"] is None


def test_complete_match_resets_the_display_to_waiting(app, authenticated_client):
    t, a, b, m = setup_match()
    db.session.add(DisplayState(mode="winner"))
    db.session.commit()
    authenticated_client.post(f"/api/match/{m.id}/complete", json={"winner_id": a.id})
    assert DisplayState.query.one().mode == "waiting"


def test_set_current_match_unsets_the_other_current_match(app, authenticated_client):
    t, a, b, first = setup_match(is_current=True)
    second = make_match(t, 1, 2, a, b)
    authenticated_client.post(f"/api/match/{second.id}/set-current")
    db.session.expire_all()
    assert second.is_current is True and first.is_current is False


@pytest.mark.xfail(strict=True, reason="DR-02: missing record renders the broken 404 page")
def test_missing_match_is_404(app, authenticated_client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert authenticated_client.get("/api/match/9999").status_code == 404


# ---- bracket, next match, stats, teams --------------------------------------------------

def test_bracket_lists_matches_in_round_order(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    make_match(t, 2, 1)
    make_match(t, 1, 2, a, b)
    make_match(t, 1, 1, a, b)
    data = authenticated_client.get(f"/api/tournament/{t.id}/bracket").get_json()
    assert [(m["round_number"], m["match_number"]) for m in data] == [(1, 1), (1, 2), (2, 1)]


def test_next_match_is_none_when_nothing_is_playable(app, authenticated_client):
    t = make_tournament()
    make_match(t)                                   # no teams yet
    assert authenticated_client.get(f"/api/tournament/{t.id}/next-match").get_json() == {"next_match": None}


def test_next_match_prefers_a_team_that_just_played(app, authenticated_client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    make_match(t, 1, 1, a, b, is_completed=True)
    make_match(t, 1, 2, c, d)                       # no continuity, comes first by order
    wanted = make_match(t, 1, 3, a, c)              # a just played: continuity wins
    nxt = authenticated_client.get(f"/api/tournament/{t.id}/next-match").get_json()["next_match"]
    assert nxt["id"] == wanted.id and nxt["is_continuity"] is True


def test_next_match_without_continuity_follows_the_order(app, authenticated_client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    first = make_match(t, 1, 1, a, b)
    make_match(t, 1, 2, c, d)
    nxt = authenticated_client.get(f"/api/tournament/{t.id}/next-match").get_json()["next_match"]
    assert nxt["id"] == first.id and nxt["is_continuity"] is False


def test_next_match_counts_a_completed_match_with_one_missing_team(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    make_match(t, 1, 1, a, None, is_completed=True)
    make_match(t, 1, 2, b, a)
    assert authenticated_client.get(f"/api/tournament/{t.id}/next-match").get_json()["next_match"] is not None


def test_stats_with_and_without_a_current_match(app, authenticated_client):
    t = make_tournament()
    assert authenticated_client.get(f"/api/tournament/{t.id}/stats").get_json() == {
        "total": 0, "completed": 0, "remaining": 0, "has_current_match": False, "current_round": None}
    a, b = make_teams(t, 2)
    make_match(t, 3, 1, a, b, is_current=True)
    make_match(t, 1, 1, a, b, is_completed=True)
    assert authenticated_client.get(f"/api/tournament/{t.id}/stats").get_json() == {
        "total": 2, "completed": 1, "remaining": 1, "has_current_match": True, "current_round": 3}


def test_tournament_teams_endpoint(app, authenticated_client):
    t = make_tournament(max_teams=4)
    make_teams(t, 2)
    data = authenticated_client.get(f"/api/tournament/{t.id}/teams").get_json()
    assert data["tournament"]["registered_teams"] == 2 and len(data["teams"]) == 2


# ---- timer and display state ------------------------------------------------------------

def test_timer_update(app, client):
    t = make_tournament()
    assert client.post(f"/api/tournament/{t.id}/timer", json={"timer_duration": 90}).get_json() == {
        "success": True, "timer_duration": 90}
    assert client.post(f"/api/tournament/{t.id}/timer", json={"other": 1}).get_json()["timer_duration"] == 90


@pytest.mark.xfail(strict=True, reason="DR-17: the timer endpoint has no login check")
def test_timer_update_requires_login(app, client):
    t = make_tournament()
    r = client.post(f"/api/tournament/{t.id}/timer", json={"timer_duration": 1})
    assert r.status_code in (301, 302, 401, 403)


@pytest.mark.xfail(strict=True, reason="DR-17: display/mode has no login check")
def test_display_mode_requires_login(app, client):
    r = client.post("/api/display/mode", json={"mode": "scoreboard"})
    assert r.status_code in (301, 302, 401, 403)


def test_display_state_default_is_created_once(app, client):
    data = client.get("/api/display/state").get_json()
    assert data["mode"] == "waiting" and "--ru-primary" in data["theme_css"]
    client.get("/api/display/state")
    assert DisplayState.query.count() == 1


def test_display_state_waiting_mode_shows_the_current_match_as_next(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, 1, 1, a, b, is_current=True)
    db.session.add(DisplayState(mode="waiting", tournament_id=t.id))
    db.session.commit()
    data = client.get("/api/display/state").get_json()
    assert data["tournament"]["id"] == t.id and data["current_match"]["id"] == m.id
    assert data["next_match"]["match_id"] == m.id and data["next_match"]["team1"]["id"] == a.id


def test_display_state_waiting_mode_with_a_half_empty_current_match(app, client):
    t = make_tournament()
    make_match(t, 1, 1, None, None, is_current=True)
    db.session.add(DisplayState(mode="waiting", tournament_id=t.id))
    db.session.commit()
    nxt = client.get("/api/display/state").get_json()["next_match"]
    assert nxt["team1"] is None and nxt["team2"] is None


def test_display_state_scoreboard_mode_shows_the_next_upcoming_match(app, client):
    t = make_tournament()
    a, b, c, d = make_teams(t, 4)
    make_match(t, 1, 1, a, b, is_current=True)
    upcoming = make_match(t, 1, 2, c, d)
    db.session.add(DisplayState(mode="scoreboard", tournament_id=t.id))
    db.session.commit()
    nxt = client.get("/api/display/state").get_json()["next_match"]
    assert nxt["match_id"] == upcoming.id and nxt["is_finals"] is True


def test_display_state_scoreboard_mode_without_upcoming_match(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    make_match(t, 1, 1, a, b, is_current=True)
    db.session.add(DisplayState(mode="scoreboard", tournament_id=t.id))
    db.session.commit()
    assert "next_match" not in client.get("/api/display/state").get_json()


def test_display_state_for_a_missing_tournament_or_no_current_match(app, client):
    db.session.add(DisplayState(mode="waiting", tournament_id=9999))
    db.session.commit()
    data = client.get("/api/display/state").get_json()
    assert "tournament" not in data
    t = make_tournament()
    DisplayState.query.one().tournament_id = t.id
    db.session.commit()
    assert "current_match" not in client.get("/api/display/state").get_json()


def test_set_display_mode_updates_the_fields_sent(app, client):
    t = make_tournament()
    data = client.post("/api/display/mode", json={
        "mode": "bracket", "tournament_id": t.id, "show_players": False, "winner_team_id": 5,
        "theme": "dark-orange"}).get_json()
    assert data["mode"] == "bracket" and data["tournament_id"] == t.id and data["show_players"] is False


def test_set_display_mode_ignores_an_unknown_theme(app, client):
    assert client.post("/api/display/mode", json={"theme": "no-such-theme"}).status_code == 200


@pytest.mark.xfail(strict=True, reason="DR-15: sanitize_message is not imported in api.py (NameError)")
def test_set_display_mode_with_a_custom_message(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    r = client.post("/api/display/mode", json={"custom_message": "<b>Hi</b>"})
    assert r.status_code == 200 and "&lt;b&gt;" in r.get_json()["custom_message"]


# ---- themes -----------------------------------------------------------------------------

def test_theme_list(app, client):
    themes = client.get("/api/themes").get_json()
    assert themes and all({"id", "name", "type", "primary"} <= set(t) for t in themes)
    assert "dark-orange" in [t["id"] for t in themes]


@pytest.mark.parametrize("payload,status,error", [
    ({}, 400, "No JSON data received"),
    ({"x": 1}, 400, "No theme specified"),
    ({"theme": "bogus"}, 400, "Invalid theme: bogus"),
])
def test_set_theme_rejections(app, authenticated_client, payload, status, error):
    r = authenticated_client.post("/api/display/theme", json=payload)
    assert r.status_code == status and r.get_json()["error"] == error


def test_set_theme_success(app, authenticated_client):
    r = authenticated_client.post("/api/display/theme", json={"theme": "dark-orange"})
    assert r.get_json() == {"success": True, "theme": "dark-orange"}


# ---- TV pairing and control -------------------------------------------------------------

def test_pair_tv_by_code(app, authenticated_client):
    make_tv("ABC234")
    data = authenticated_client.post("/api/tv/pair", json={"code": "abc234"}).get_json()
    assert data["success"] is True and data["tv_session"]["code"] == "ABC234"
    authenticated_client.post("/api/tv/pair", json={"code": "ABC234"})    # pairing twice keeps one entry
    with authenticated_client.session_transaction() as s:
        assert s["tv_codes"] == ["ABC234"] and s["tv_code"] == "ABC234"


def test_pair_tv_with_an_unknown_code(app, authenticated_client):
    r = authenticated_client.post("/api/tv/pair", json={"code": "NOPE99"})
    assert r.status_code == 404 and r.get_json() == {"success": False, "error": "Invalid code"}


def test_pair_all_without_and_with_tvs(app, authenticated_client):
    r = authenticated_client.post("/api/tv/pair-all")
    assert r.status_code == 404 and r.get_json()["error"] == "No active TVs found"
    make_tv("ABC234")
    make_tv("DEF567")
    make_tv("GHJ890", is_active=False)
    data = authenticated_client.post("/api/tv/pair-all").get_json()
    assert data["count"] == 2 and sorted(data["codes"]) == ["ABC234", "DEF567"]
    with authenticated_client.session_transaction() as s:
        assert s["control_all_tvs"] is True and s["tv_code"] in ("ABC234", "DEF567")


def test_unpair_clears_the_session(app, authenticated_client):
    with authenticated_client.session_transaction() as s:
        s["tv_codes"] = ["ABC234"]
        s["tv_code"] = "DEF567"          # not in the list: the code is added before notifying
        s["control_all_tvs"] = True
    assert authenticated_client.post("/api/tv/unpair").get_json() == {"success": True}
    with authenticated_client.session_transaction() as s:
        assert not {"tv_codes", "tv_code", "control_all_tvs"} & set(s)


def test_unpair_with_nothing_paired(app, authenticated_client):
    assert authenticated_client.post("/api/tv/unpair").get_json() == {"success": True}


def test_validate_tv_codes(app, authenticated_client):
    make_tv("ACT234")
    make_tv("OLD234", last_seen=datetime.utcnow() - timedelta(minutes=10))
    assert authenticated_client.post("/api/tv/validate", json={"codes": []}).get_json() == {
        "active": [], "inactive": []}
    data = authenticated_client.post("/api/tv/validate", json={"codes": ["act234", "OLD234", "NOPE99"]}).get_json()
    assert data == {"active": ["act234"], "inactive": ["OLD234", "NOPE99"]}


def test_tv_session_list_only_shows_recent_active_tvs(app, authenticated_client):
    make_tv("NEW234")
    make_tv("OLD234", last_seen=datetime.utcnow() - timedelta(hours=2))
    make_tv("OFF234", is_active=False)
    codes = [s["code"] for s in authenticated_client.get("/api/tv/sessions").get_json()]
    assert codes == ["NEW234"]


def test_tv_state_and_heartbeat_update_last_seen(app, client):
    tv = make_tv("ABC234", last_seen=datetime.utcnow() - timedelta(hours=1))
    before = tv.last_seen
    assert client.get("/api/tv/abc234/state").get_json()["code"] == "ABC234"
    db.session.expire_all()
    assert TVSession.query.one().last_seen > before
    hb = client.post("/api/tv/ABC234/heartbeat").get_json()
    assert hb["success"] is True and "last_seen" in hb


def test_tv_state_and_heartbeat_for_an_unknown_tv(app, client):
    assert client.get("/api/tv/NOPE99/state").status_code == 404
    assert client.post("/api/tv/NOPE99/heartbeat").status_code == 404


def test_control_tv_unknown_code(app, authenticated_client):
    r = authenticated_client.post("/api/tv/NOPE99/control", json={"mode": "x"})
    assert r.status_code == 404 and r.get_json() == {"error": "TV not found"}


def test_control_tv_updates_fields_and_can_redirect_to_live(app, authenticated_client):
    t = make_tournament()
    make_tv("ABC234")
    data = authenticated_client.post("/api/tv/abc234/control", json={
        "mode": "scoreboard", "winner_team_id": None, "tournament_id": t.id, "redirect_to_live": True}).get_json()
    assert data["success"] is True
    tv = TVSession.query.one()
    assert tv.mode == "scoreboard" and tv.tournament_id == t.id


def test_control_tv_with_no_fields_changes_nothing(app, authenticated_client):
    make_tv("ABC234")
    assert authenticated_client.post("/api/tv/ABC234/control", json={}).get_json()["success"] is True
    assert TVSession.query.one().mode == "waiting"


@pytest.mark.xfail(strict=True, reason="DR-15: sanitize_message is not imported in api.py (NameError)")
def test_control_tv_with_a_custom_message(app, authenticated_client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    make_tv("ABC234")
    r = authenticated_client.post("/api/tv/ABC234/control", json={"custom_message": "Hello"})
    assert r.status_code == 200


# ---- bracket self-test endpoint ---------------------------------------------------------

def test_generate_brackets_self_test_covers_every_format(app, authenticated_client):
    data = authenticated_client.post("/api/test/generate-brackets").get_json()
    assert set(data) == {"single_elimination", "double_elimination", "round_robin",
                         "round_robin_playoffs", "swiss"}
    assert data["single_elimination"]["4"]["match_count"] > 0
    assert Tournament.query.count() == 0 and Team.query.count() == 0     # it cleans up after itself


def test_generate_brackets_reports_an_error_for_a_format_that_raises(app, authenticated_client, monkeypatch):
    import app.blueprints.bracket as bracket

    def boom(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(bracket, "create_swiss_round", boom)
    data = authenticated_client.post("/api/test/generate-brackets").get_json()
    assert data["swiss"]["4"] == {"error": "boom"}
    assert Tournament.query.count() == 0
