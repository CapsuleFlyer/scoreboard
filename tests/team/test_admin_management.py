"""Whole-app tests: the admin routes outside registration (teams, tournaments, matches, users,
start tournament, API tokens). Registration routes are in test_admin_registration.py.
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest

from app import db
from app.blueprints.admin import calculate_standings
from app.models import Admin, APIToken, Match, Team, Tournament
from team_support import make_team, make_tournament
from team_support_more import flashes, make_global_team, make_match, make_teams, make_token

FORMATS = ["single_elimination", "double_elimination", "round_robin", "round_robin_playoffs",
           "swiss", "no_such_format"]


# ---- access: every route below needs a login --------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/admin/"), ("get", "/admin/teams"), ("post", "/admin/teams"),
    ("post", "/admin/teams/1/delete"), ("get", "/admin/tournaments"), ("post", "/admin/tournaments"),
    ("get", "/admin/tournaments/1"), ("post", "/admin/tournaments/1/delete"),
    ("post", "/admin/tournaments/1/advance-to-playoffs"), ("post", "/admin/match/1/edit"),
    ("get", "/admin/users"), ("post", "/admin/users/add"), ("post", "/admin/users/2/delete"),
    ("post", "/admin/users/2/change-password"), ("post", "/admin/tournament/1/start"),
    ("post", "/admin/tournament/1/regenerate-code"), ("get", "/admin/api-tokens"),
    ("post", "/admin/api-tokens/create"), ("post", "/admin/api-tokens/1/revoke"),
    ("post", "/admin/api-tokens/1/delete"), ("get", "/admin/api-tokens/list"),
])
def test_admin_routes_redirect_anonymous_visitors_to_login(app, client, method, path):
    r = getattr(client, method)(path)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ---- dashboard and global teams ---------------------------------------------------------

def test_dashboard_and_team_page_render(app, authenticated_client):
    make_global_team("Loose")
    assert authenticated_client.get("/admin/").status_code == 200
    r = authenticated_client.get("/admin/teams")
    assert r.status_code == 200 and "Loose" in r.get_data(as_text=True)


def test_create_global_team(app, authenticated_client):
    r = authenticated_client.post("/admin/teams", data={"name": "Robots", "player1": "Ann", "player2": "Bob"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/teams")
    team = Team.query.filter_by(name="Robots").one()
    assert team.tournament_id is None and (team.player1, team.player2) == ("Ann", "Bob")


@pytest.mark.parametrize("missing", ["name", "player1", "player2"])
def test_create_global_team_needs_all_fields(app, authenticated_client, missing):
    data = {"name": "Robots", "player1": "Ann", "player2": "Bob", missing: "  "}
    authenticated_client.post("/admin/teams", data=data)
    assert Team.query.count() == 0
    assert "All fields are required" in flashes(authenticated_client)


def test_create_global_team_refuses_duplicate_name_ignoring_case(app, authenticated_client):
    make_global_team("Robots")
    authenticated_client.post("/admin/teams", data={"name": "ROBOTS", "player1": "Ann", "player2": "Bob"})
    assert Team.query.count() == 1
    assert any("already exists" in m for m in flashes(authenticated_client))


def test_create_global_team_allows_same_name_inside_a_tournament(app, authenticated_client):
    t = make_tournament()
    make_team(t, "Robots")          # belongs to a tournament, so it is not a global duplicate
    authenticated_client.post("/admin/teams", data={"name": "Robots", "player1": "Ann", "player2": "Bob"})
    assert Team.query.filter_by(tournament_id=None).count() == 1


def test_delete_global_team(app, authenticated_client):
    team = make_global_team()
    r = authenticated_client.post(f"/admin/teams/{team.id}/delete")
    assert r.status_code == 302 and Team.query.count() == 0


@pytest.mark.xfail(strict=True, reason="DR-02: missing record renders the broken 404 page")
def test_delete_missing_team_is_404(app, authenticated_client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert authenticated_client.post("/admin/teams/9999/delete").status_code == 404


# ---- creating tournaments ---------------------------------------------------------------

def test_tournament_list_page_shows_own_and_unowned_tournaments(app, authenticated_client):
    make_tournament(name="Mine", owner_id=1)
    make_tournament(name="Nobody", owner_id=None, registration_code="N1")
    make_tournament(name="Theirs", owner_id=2, registration_code="T2")
    page = authenticated_client.get("/admin/tournaments").get_data(as_text=True)
    assert "Mine" in page and "Nobody" in page and "Theirs" not in page


def test_create_open_tournament_with_custom_settings(app, authenticated_client):
    r = authenticated_client.post("/admin/tournaments", data={
        "name": "Cup", "registration_mode": "open", "registration_code": "abc123",
        "max_teams": "8", "min_teams": "2", "timer_minutes": "1", "timer_seconds": "5",
        "format": "round_robin", "require_email": "on", "require_player_names": "on"})
    t = Tournament.query.filter_by(name="Cup").one()
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/admin/tournament/{t.id}/registrations")
    assert (t.registration_code, t.max_teams, t.min_teams, t.timer_duration) == ("ABC123", 8, 2, 65)
    assert (t.registration_open, t.status, t.format, t.owner_id) == (True, "registration", "round_robin", 1)
    assert (t.require_email, t.require_player_names, t.require_confirmation) == (True, True, False)


def test_create_open_tournament_uses_defaults(app, authenticated_client):
    authenticated_client.post("/admin/tournaments", data={"name": "Plain", "registration_mode": "open"})
    t = Tournament.query.filter_by(name="Plain").one()
    assert (t.max_teams, t.min_teams, t.timer_duration, t.format) == (16, 4, 150, "single_elimination")
    assert len(t.registration_code) == 6


def test_create_tournament_requires_a_name(app, authenticated_client):
    authenticated_client.post("/admin/tournaments", data={"name": "   "})
    assert Tournament.query.count() == 0
    assert "Tournament name is required" in flashes(authenticated_client)


@pytest.mark.parametrize("fmt", FORMATS)
def test_create_closed_tournament_builds_a_bracket_for_every_format(app, authenticated_client, fmt):
    teams = [make_global_team(f"T{i}") for i in range(1, 5)]
    r = authenticated_client.post("/admin/tournaments", data={
        "name": f"Closed {fmt}", "registration_mode": "closed", "format": fmt,
        "teams": [str(t.id) for t in teams]})
    t = Tournament.query.filter_by(name=f"Closed {fmt}").one()
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/admin/tournaments/{t.id}")
    assert (t.registration_open, t.status) == (False, "ready")
    assert Match.query.filter_by(tournament_id=t.id).count() > 0


# ---- viewing, standings, deleting -------------------------------------------------------

@pytest.mark.parametrize("fmt", ["single_elimination", "round_robin", "round_robin_playoffs", "swiss"])
def test_view_tournament_renders_for_each_format(app, authenticated_client, fmt):
    t = make_tournament(format=fmt)
    a, b = make_teams(t, 2)
    make_match(t, team1=a, team2=b, score1=2, score2=1, is_completed=True, winner_id=a.id)
    assert authenticated_client.get(f"/admin/tournaments/{t.id}").status_code == 200


def test_calculate_standings_ranks_by_wins_then_difference_then_points(app):
    t = make_tournament(format="round_robin")
    a, b, c = make_teams(t, 3)
    make_match(t, 1, 1, a, b, 5, 3, is_completed=True, winner_id=a.id)
    make_match(t, 1, 2, b, c, 4, 1, is_completed=True, winner_id=b.id)
    make_match(t, 1, 3, c, a, 2, 2, is_completed=True)                 # draw: no winner
    make_match(t, 1, 4, a, None, 3, 0, is_completed=True, winner_id=a.id)   # bye
    make_match(t, 1, 5, b, c, 9, 0)                                    # not completed: ignored
    table = calculate_standings(t.id)
    assert [row["team_id"] for row in table] == [a.id, b.id, c.id]
    assert [row["rank"] for row in table] == [1, 2, 3]
    top = table[0]
    assert (top["wins"], top["losses"], top["points_for"], top["points_against"], top["matches_played"],
            top["point_diff"]) == (2, 0, 10, 5, 3, 5)
    assert (table[1]["wins"], table[1]["losses"], table[1]["point_diff"]) == (1, 1, 1)
    assert (table[2]["wins"], table[2]["losses"], table[2]["point_diff"]) == (0, 1, -3)


def test_calculate_standings_empty(app):
    t = make_tournament()
    assert calculate_standings(t.id) == []


def test_delete_tournament_removes_its_matches(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    make_match(t, team1=a, team2=b)
    r = authenticated_client.post(f"/admin/tournaments/{t.id}/delete")
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/tournaments")
    assert db.session.get(Tournament, t.id) is None and Match.query.count() == 0


def _playoff_setup():
    t = make_tournament(format="round_robin_playoffs")
    a, b, c, d = make_teams(t, 4)
    make_match(t, 1, 1, a, b, 3, 0, is_completed=True, winner_id=a.id)
    make_match(t, 1, 2, c, d, 2, 1, is_completed=True, winner_id=c.id)
    make_match(t, 1, 3, a, d, 3, 0, is_completed=True, winner_id=a.id)
    make_match(t, 1, 4, c, b, 2, 0, is_completed=True, winner_id=c.id)
    return t, (a, b, c, d)


def test_advance_to_playoffs_seeds_the_semifinals(app, authenticated_client):
    t, (a, b, c, d) = _playoff_setup()
    s1 = make_match(t, 100, 1)
    s2 = make_match(t, 100, 2)
    r = authenticated_client.post(f"/admin/tournaments/{t.id}/advance-to-playoffs")
    assert r.status_code == 302
    db.session.expire_all()
    # standings are A, C, D, B: first meets fourth, second meets third
    assert (s1.team1_id, s1.team2_id, s2.team1_id, s2.team2_id) == (a.id, b.id, c.id, d.id)
    assert s1.is_current is True and db.session.get(Tournament, t.id).current_phase == "playoffs"


def test_advance_to_playoffs_ignores_other_formats(app, authenticated_client):
    t = make_tournament(format="single_elimination")
    before = t.current_phase
    assert authenticated_client.post(f"/admin/tournaments/{t.id}/advance-to-playoffs").status_code == 302
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).current_phase == before


def test_advance_to_playoffs_needs_four_teams_in_the_standings(app, authenticated_client):
    t = make_tournament(format="round_robin_playoffs")
    a, b = make_teams(t, 2)
    make_match(t, 1, 1, a, b, 1, 0, is_completed=True, winner_id=a.id)
    make_match(t, 100, 1)
    make_match(t, 100, 2)
    authenticated_client.post(f"/admin/tournaments/{t.id}/advance-to-playoffs")
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).current_phase != "playoffs"


def test_advance_to_playoffs_without_two_semifinals_changes_nothing(app, authenticated_client):
    t, _ = _playoff_setup()
    make_match(t, 100, 1)                       # only one semifinal
    authenticated_client.post(f"/admin/tournaments/{t.id}/advance-to-playoffs")
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).current_phase != "playoffs"


# ---- editing a match by hand ------------------------------------------------------------

def _edit_setup():
    t = make_tournament()
    a, b = make_teams(t, 2)
    return t, a, b, make_match(t, team1=a, team2=b, is_current=True)


def test_edit_match_mark_complete_sets_winner_and_clears_current(app, authenticated_client):
    t, a, b, m = _edit_setup()
    r = authenticated_client.post(f"/admin/match/{m.id}/edit", data={
        "team1_id": str(a.id), "team2_id": str(b.id), "team1_score": "3", "team2_score": "1",
        "action": "mark_complete", "winner_id": str(a.id)})
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/admin/tournaments/{t.id}")
    db.session.expire_all()
    assert (m.team1_score, m.team2_score, m.is_completed, m.is_current, m.winner_id) == (3, 1, True, False, a.id)


def test_edit_match_mark_complete_with_blank_winner(app, authenticated_client):
    t, a, b, m = _edit_setup()
    authenticated_client.post(f"/admin/match/{m.id}/edit", data={"action": "mark_complete", "winner_id": " "})
    db.session.expire_all()
    assert m.is_completed is True and m.winner_id is None and m.team1_id is None and m.team2_id is None


def test_edit_match_reset_clears_result_and_scores(app, authenticated_client):
    t, a, b, m = _edit_setup()
    m.is_completed, m.winner_id, m.team1_score = True, a.id, 5
    db.session.commit()
    authenticated_client.post(f"/admin/match/{m.id}/edit", data={"action": "reset", "team1_score": "5",
                                                                  "team2_score": "2"})
    db.session.expire_all()
    assert (m.is_completed, m.winner_id, m.team1_score, m.team2_score) == (False, None, 0, 0)


def test_edit_match_set_current_unsets_the_previous_current_match(app, authenticated_client):
    t, a, b, first = _edit_setup()
    second = make_match(t, 1, 2, a, b)
    authenticated_client.post(f"/admin/match/{second.id}/edit", data={"action": "set_current"})
    db.session.expire_all()
    assert second.is_current is True and first.is_current is False and second.is_completed is False


def test_edit_match_without_action_only_saves_fields(app, authenticated_client):
    t, a, b, m = _edit_setup()
    authenticated_client.post(f"/admin/match/{m.id}/edit", data={
        "team1_id": str(b.id), "team2_id": str(a.id), "team1_score": "2", "team2_score": "4"})
    db.session.expire_all()
    assert (m.team1_id, m.team2_id, m.team1_score, m.team2_score) == (b.id, a.id, 2, 4)
    assert m.is_completed is False


def test_edit_match_ignores_a_score_that_is_not_a_number(app, authenticated_client):
    t, a, b, m = _edit_setup()
    m.team1_score = 7
    db.session.commit()
    r = authenticated_client.post(f"/admin/match/{m.id}/edit", data={"team1_score": "abc", "team2_score": "2"})
    assert r.status_code == 302
    db.session.expire_all()
    assert m.team1_score == 7


# ---- admin users ------------------------------------------------------------------------

def test_user_pages_and_add_user(app, authenticated_client):
    assert authenticated_client.get("/admin/users").status_code == 200
    r = authenticated_client.post("/admin/users/add", data={"username": "bob", "password": "pw12345"})
    assert r.status_code == 302
    bob = Admin.query.filter_by(username="bob").one()
    assert bob.check_password("pw12345") and bob.password_hash != "pw12345"
    assert "Admin bob created" in flashes(authenticated_client)


def test_add_user_refuses_a_duplicate_username(app, authenticated_client):
    authenticated_client.post("/admin/users/add", data={"username": "testadmin", "password": "x"})
    assert Admin.query.filter_by(username="testadmin").count() == 1
    assert "Username already exists" in flashes(authenticated_client)


def test_admin_cannot_delete_their_own_account(app, authenticated_client):
    authenticated_client.post("/admin/users/1/delete")      # the session admin_id is 1
    assert db.session.get(Admin, 1) is not None
    assert "Cannot delete your own account" in flashes(authenticated_client)


def test_admin_can_delete_another_admin(app, authenticated_client):
    authenticated_client.post("/admin/users/2/delete")
    assert db.session.get(Admin, 2) is None


def test_change_password_replaces_the_hash(app, authenticated_client):
    authenticated_client.post("/admin/users/2/change-password", data={"password": "brand-new"})
    db.session.expire_all()
    user = db.session.get(Admin, 2)
    assert user.check_password("brand-new") and not user.check_password("testpassword")


# ---- start tournament, regenerate code --------------------------------------------------

def test_start_refuses_when_too_few_confirmed_teams(app, authenticated_client):
    t = make_tournament()                    # min_teams defaults to 4
    make_teams(t, 3)
    r = authenticated_client.post(f"/admin/tournament/{t.id}/start")
    assert r.status_code == 400 and r.get_json() == {
        "success": False, "error": "Need at least 4 confirmed teams to start"}
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).status == "registration"


def test_start_does_not_count_unconfirmed_teams(app, authenticated_client):
    t = make_tournament()
    make_teams(t, 2, confirmed=True)
    for i in range(2):
        make_team(t, f"P{i}", confirmed=False)
    assert authenticated_client.post(f"/admin/tournament/{t.id}/start").status_code == 400


@pytest.mark.parametrize("fmt", FORMATS)
def test_start_generates_the_bracket_for_every_format(app, authenticated_client, fmt):
    t = make_tournament(format=fmt)
    make_teams(t, 4)
    r = authenticated_client.post(f"/admin/tournament/{t.id}/start")
    data = r.get_json()
    assert r.status_code == 200 and data["success"] is True and data["team_count"] == 4
    db.session.expire_all()
    t = db.session.get(Tournament, t.id)
    assert (t.status, t.registration_open, t.current_phase) == ("in_progress", False, "bracket")
    assert Match.query.filter_by(tournament_id=t.id).count() > 0


def test_start_falls_back_to_defaults_when_min_teams_and_format_are_null(app, authenticated_client):
    t = make_tournament()
    t.min_teams, t.format = None, None
    db.session.commit()
    make_teams(t, 1)
    assert authenticated_client.post(f"/admin/tournament/{t.id}/start").get_json()["error"] == \
        "Need at least 2 confirmed teams to start"
    make_team(t, "Second")
    assert authenticated_client.post(f"/admin/tournament/{t.id}/start").status_code == 200


def test_regenerate_code_issues_a_new_six_character_code(app, authenticated_client):
    t = make_tournament(registration_code="OLD123")
    data = authenticated_client.post(f"/admin/tournament/{t.id}/regenerate-code").get_json()
    assert data["success"] is True and data["code"] != "OLD123" and len(data["code"]) == 6
    db.session.expire_all()
    assert db.session.get(Tournament, t.id).registration_code == data["code"]


# ---- API tokens -------------------------------------------------------------------------

def test_token_pages_render(app, authenticated_client):
    make_token()
    assert authenticated_client.get("/admin/api-tokens").status_code == 200
    listing = authenticated_client.get("/admin/api-tokens/list").get_json()["tokens"]
    assert len(listing) == 1 and listing[0]["name"] == "t"


def test_create_token_returns_the_secret_once_and_stores_only_its_hash(app, authenticated_client):
    data = authenticated_client.post("/admin/api-tokens/create", json={
        "name": "Robot", "permissions": ["match:read"], "expires_days": 7}).get_json()
    assert data["success"] is True and data["token_info"]["permissions"] == ["match:read"]
    assert data["token_info"]["expires_at"] is not None
    row = APIToken.query.one()
    assert row.token_hash == APIToken.hash_token(data["token"]) and data["token"] not in row.token_hash
    assert row.token_prefix == data["token"][:8] and row.admin_id == 1


def test_create_token_defaults(app, authenticated_client):
    data = authenticated_client.post("/admin/api-tokens/create", json={"name": "   "}).get_json()
    assert data["token_info"]["name"] == "Unnamed Token"
    assert data["token_info"]["permissions"] == APIToken.SCOPES
    assert data["token_info"]["tournament_id"] is None and data["token_info"]["expires_at"] is None


@pytest.mark.parametrize("permissions,expected", [
    ('["team:read"]', ["team:read"]),              # permissions sent as a JSON string
    ("not json", APIToken.SCOPES),                 # unreadable string falls back to all scopes
    ([], APIToken.SCOPES),                         # empty list falls back to all scopes
])
def test_create_token_permission_inputs(app, authenticated_client, permissions, expected):
    data = authenticated_client.post("/admin/api-tokens/create",
                                     json={"name": "x", "permissions": permissions}).get_json()
    assert data["token_info"]["permissions"] == expected


def test_create_token_scoped_to_a_tournament(app, authenticated_client):
    t = make_tournament()
    data = authenticated_client.post("/admin/api-tokens/create",
                                     json={"name": "x", "tournament_id": str(t.id)}).get_json()
    assert data["token_info"]["tournament_id"] == t.id and data["token_info"]["tournament_name"] == t.name


def test_revoke_and_delete_own_token(app, authenticated_client):
    token, _ = make_token()
    r = authenticated_client.post(f"/admin/api-tokens/{token.id}/revoke")
    assert r.get_json() == {"success": True, "message": "Token revoked"}
    db.session.expire_all()
    assert db.session.get(APIToken, token.id).is_active is False
    r = authenticated_client.post(f"/admin/api-tokens/{token.id}/delete")
    assert r.get_json() == {"success": True, "message": "Token deleted"}
    assert db.session.get(APIToken, token.id) is None


@pytest.mark.parametrize("action", ["revoke", "delete"])
def test_token_of_another_admin_cannot_be_touched(app, authenticated_client, action):
    other, _ = make_token(admin_id=2)
    mine_missing = authenticated_client.post(f"/admin/api-tokens/9999/{action}")
    theirs = authenticated_client.post(f"/admin/api-tokens/{other.id}/{action}")
    for r in (mine_missing, theirs):
        assert r.status_code == 404 and r.get_json() == {"success": False, "error": "Token not found"}
    db.session.expire_all()
    assert db.session.get(APIToken, other.id).is_active is True


def test_token_list_shows_only_own_tokens(app, authenticated_client):
    make_token(admin_id=1, name="mine")
    make_token(admin_id=2, name="theirs")
    names = [t["name"] for t in authenticated_client.get("/admin/api-tokens/list").get_json()["tokens"]]
    assert names == ["mine"]
