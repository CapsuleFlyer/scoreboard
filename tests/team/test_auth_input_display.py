"""Whole-app tests: auth.py, main.py, input.py, display.py.
Status: written against the source (READ). Run on your machine before citing any result.

New suspected defects, kept as strict xfail so a run confirms or refutes them:
  DR-14  input.py never imports `db`, so every route that calls db.get_or_404 raises NameError
  DR-02  missing record gives 500 through the broken 404 page (see test_admin_registration.py)
"""
import pytest
from flask import session

from app import db
from app.blueprints.auth import (admin_or_tv_required, api_login_required, get_current_admin,
                                 login_required, socket_login_required)
from app.models import Admin, TVSession
from team_support import make_tournament
from team_support_more import flashes, make_match, make_tv

# ---- login / logout ---------------------------------------------------------------------

def test_login_page_renders(app, client):
    assert client.get("/login").status_code == 200


def test_login_success_sets_session_and_redirects_to_dashboard(app, client):
    r = client.post("/login", data={"username": "testadmin", "password": "testpassword"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/")
    with client.session_transaction() as s:
        assert s["admin_username"] == "testadmin" and s["admin_id"] == 2


@pytest.mark.parametrize("user,pw", [("testadmin", "wrong"), ("nobody", "testpassword"), ("", "")])
def test_login_failure_keeps_the_user_out(app, client, user, pw):
    r = client.post("/login", data={"username": user, "password": pw})
    assert r.status_code == 200
    with client.session_transaction() as s:
        assert "admin_id" not in s


def test_login_refuses_an_inactive_admin(app, client):
    a = Admin.query.filter_by(username="testadmin").one()
    a.is_active = False
    db.session.commit()
    client.post("/login", data={"username": "testadmin", "password": "testpassword"})
    with client.session_transaction() as s:
        assert "admin_id" not in s


def test_login_admin_without_password_hash_cannot_log_in(app, client):
    db.session.add(Admin(username="nopass"))
    db.session.commit()
    client.post("/login", data={"username": "nopass", "password": "x"})
    with client.session_transaction() as s:
        assert "admin_id" not in s


@pytest.mark.parametrize("next_url,expected_suffix", [
    ("/admin/teams", "/admin/teams"),                       # relative path is allowed
    ("http://localhost/admin/users", "/admin/users"),       # same host is allowed
    ("http://evil.example/steal", "/admin/"),               # other host: ignored (open-redirect guard)
])
def test_login_next_parameter_open_redirect_guard(app, client, next_url, expected_suffix):
    r = client.post("/login", query_string={"next": next_url},
                    data={"username": "testadmin", "password": "testpassword"})
    assert r.status_code == 302 and r.headers["Location"].endswith(expected_suffix)
    assert "evil.example" not in r.headers["Location"]


def test_logout_clears_the_session_keys(app, authenticated_client):
    with authenticated_client.session_transaction() as s:
        s["tv_code"] = "ABC234"
    r = authenticated_client.get("/logout")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    with authenticated_client.session_transaction() as s:
        assert "admin_id" not in s and "admin_username" not in s and "tv_code" not in s


# ---- pairing a TV from the browser ------------------------------------------------------

def test_pair_requires_login(app, client):
    make_tv()
    r = client.get("/pair/ABC234")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_pair_valid_code_without_tournament_goes_to_input_index(app, authenticated_client):
    make_tv("ABC234")
    r = authenticated_client.get("/pair/abc234")          # lower case is accepted
    assert r.status_code == 302 and r.headers["Location"].endswith("/input/")
    with authenticated_client.session_transaction() as s:
        assert s["tv_code"] == "ABC234"


def test_pair_valid_code_with_tournament_goes_to_the_ipad_page(app, authenticated_client):
    t = make_tournament()
    make_tv("ABC234", tournament_id=t.id)
    r = authenticated_client.get("/pair/ABC234")
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/input/tournament/{t.id}/ipad")


def test_pair_invalid_code_is_refused(app, authenticated_client):
    r = authenticated_client.get("/pair/ZZZZZZ")
    assert r.status_code == 302 and r.headers["Location"].endswith("/input/")
    assert "Invalid TV code" in flashes(authenticated_client)
    with authenticated_client.session_transaction() as s:
        assert "tv_code" not in s


def test_pair_ignores_an_inactive_tv(app, authenticated_client):
    make_tv("ABC234", is_active=False)
    authenticated_client.get("/pair/ABC234")
    assert "Invalid TV code" in flashes(authenticated_client)


# ---- the decorators (called directly inside a request context) --------------------------

def _call(app, decorator, session_values):
    @decorator
    def view():
        return "ran"
    with app.test_request_context():
        for k, v in session_values.items():
            session[k] = v
        return view()


def test_login_required_decorator_branches(app):
    assert _call(app, login_required, {"admin_id": 1}) == "ran"
    assert _call(app, login_required, {}).status_code == 302


def test_api_login_required_returns_401_json(app):
    assert _call(app, api_login_required, {"admin_id": 1}) == "ran"
    resp, status = _call(app, api_login_required, {})
    assert status == 401 and resp.get_json() == {"error": "Authentication required"}


def test_socket_login_required_ignores_anonymous_calls(app):
    assert _call(app, socket_login_required, {"admin_id": 1}) == "ran"
    assert _call(app, socket_login_required, {}) is None


def test_admin_or_tv_required_accepts_admin_or_active_tv_only(app):
    tv = make_tv("ABC234")
    gone = make_tv("DEF567", is_active=False)
    assert _call(app, admin_or_tv_required, {"admin_id": 1}) == "ran"
    assert _call(app, admin_or_tv_required, {"tv_session_id": tv.id}) == "ran"
    for values in ({}, {"tv_session_id": gone.id}, {"tv_session_id": 9999}):
        resp, status = _call(app, admin_or_tv_required, values)
        assert status == 401 and "Admin or TV Session required" in resp.get_json()["error"]


def test_get_current_admin(app):
    with app.test_request_context():
        assert get_current_admin() is None
        session["admin_id"] = 2
        assert get_current_admin().username == "testadmin"


# ---- main and input ---------------------------------------------------------------------

def test_landing_page(app, client):
    assert client.get("/").status_code == 200


def test_input_index_requires_login_and_renders_for_admin(app, client, authenticated_client):
    anon = app.test_client().get("/input/")
    assert anon.status_code == 302 and "/login" in anon.headers["Location"]
    assert authenticated_client.get("/input/").status_code == 200


@pytest.mark.xfail(strict=True, reason="DR-14: input.py does not import db, so db.get_or_404 raises NameError")
@pytest.mark.parametrize("path", ["/input/tournament/{t}", "/input/tournament/{t}/remote",
                                  "/input/tournament/{t}/ipad", "/input/match/{m}"])
def test_input_pages_for_an_existing_record_render(app, authenticated_client, path):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    t = make_tournament()
    m = make_match(t)
    assert authenticated_client.get(path.format(t=t.id, m=m.id)).status_code == 200


@pytest.mark.parametrize("path", ["/input/tournament/1", "/input/tournament/1/remote",
                                  "/input/tournament/1/ipad", "/input/match/1"])
def test_input_pages_need_login(app, client, path):
    r = client.get(path)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ---- display (TV) -----------------------------------------------------------------------

def test_display_index_creates_one_tv_session_and_reuses_it(app, client):
    assert client.get("/display/").status_code == 200
    first = TVSession.query.one()
    assert client.get("/display/").status_code == 200
    assert TVSession.query.count() == 1 and TVSession.query.one().code == first.code


def test_display_index_replaces_an_inactive_session(app, client):
    client.get("/display/")
    old = TVSession.query.one()
    old.is_active = False
    db.session.commit()
    client.get("/display/")
    assert TVSession.query.count() == 2


@pytest.mark.parametrize("path", ["/display/tournament/{t}", "/display/bracket/{t}",
                                  "/display/scoreboard/{t}"])
def test_display_pages_render_with_and_without_matches(app, client, path):
    t = make_tournament()
    assert client.get(path.format(t=t.id)).status_code == 200
    from app.models import Team
    a = Team(name="A", player1="a", player2="b", tournament_id=t.id)
    b = Team(name="B", player1="c", player2="d", tournament_id=t.id)
    db.session.add_all([a, b])
    db.session.commit()
    make_match(t, team1=a, team2=b, is_current=True)
    assert client.get(path.format(t=t.id)).status_code == 200


@pytest.mark.xfail(strict=True, reason="DR-02: missing tournament renders the broken 404 page")
def test_display_page_for_missing_tournament_is_404(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert client.get("/display/tournament/9999").status_code == 404


def test_display_live_creates_session_and_follows_the_tournament(app, client):
    t1 = make_tournament(registration_code="AAA111")
    t2 = make_tournament(registration_code="BBB222")
    assert client.get(f"/display/live/{t1.id}").status_code == 200
    tv = TVSession.query.one()
    assert tv.tournament_id == t1.id and tv.mode == "waiting"
    client.get(f"/display/live/{t1.id}")                     # same tournament: unchanged
    assert TVSession.query.one().tournament_id == t1.id
    client.get(f"/display/live/{t2.id}")                     # other tournament: session moves
    db.session.expire_all()
    assert TVSession.query.count() == 1 and TVSession.query.one().tournament_id == t2.id
