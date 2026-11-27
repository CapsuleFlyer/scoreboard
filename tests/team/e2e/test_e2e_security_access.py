"""Security checks through the running application (area 3, section 4 of the brief).

Part 1, access matrix: two roles (visitor = no login, admin) against both workflows. Every row is
recorded in docs/evidence/security/access-matrix.csv with role, action, expected result, observed
result and evidence, and each decision is asserted. Rows that only observe a control (cookie
attributes, headers) go to controls.csv and are never failed, so they can be reported as findings.

CSRF is ON in this server (like production), so state-changing calls without a token are refused.
Status: written against the templates and routes (READ). Run on your machine before citing results.
"""
import csv
import re

import pytest
from playwright.sync_api import expect

from e2e_helpers import EVIDENCE, admin_login

OUT = EVIDENCE.parent / "security"
ROWS, CONTROLS = [], []
DENIED = (302, 400, 401, 403)


@pytest.fixture(scope="module", autouse=True)
def write_evidence():
    yield
    OUT.mkdir(parents=True, exist_ok=True)
    for name, header, rows in (("access-matrix.csv", ["role", "action", "expected", "observed", "evidence"], ROWS),
                               ("controls.csv", ["control", "observed", "evidence"], CONTROLS)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows([header] + rows)


@pytest.fixture
def visitor(browser, world):
    ctx = browser.new_context(base_url=world.url)
    yield ctx.request
    ctx.close()


def record(role, action, expected, observed, evidence):
    ROWS.append([role, action, expected, observed, evidence])


def pending_setup(world):
    tid = world.tournament(require_confirmation=True)
    team = world.team(tid, "Pending Co", confirmed=False)
    return tid, team


# ---- visitor (no login) -----------------------------------------------------------------

def test_visitor_can_open_the_public_registration_page(world, visitor):
    world.tournament()
    r = visitor.get("/register/tournament/REG001")
    record("visitor", "GET /register/tournament/REG001", "allowed (200)", f"HTTP {r.status}", "response status")
    assert r.status == 200


def test_visitor_can_validate_a_code_through_the_json_api(world, visitor):
    world.tournament()
    r = visitor.post("/api/register/validate-code", data={"code": "REG001"})
    record("visitor", "POST /api/register/validate-code", "allowed (200, no token needed)",
           f"HTTP {r.status}", "CSRF-exempt API blueprint (app/__init__.py line 43)")
    assert r.status == 200 and r.json()["valid"] is True


def test_visitor_cannot_open_the_admin_registrations_page(world, visitor):
    tid = world.tournament()
    r = visitor.get(f"/admin/tournament/{tid}/registrations", max_redirects=0)
    record("visitor", f"GET /admin/tournament/{tid}/registrations", "denied (redirect to /login)",
           f"HTTP {r.status} Location {r.headers.get('location')}", "login_required in app/blueprints/auth.py")
    assert r.status == 302 and "/login" in r.headers["location"]


def test_visitor_cannot_open_the_admin_dashboard(world, visitor):
    r = visitor.get("/admin/", max_redirects=0)
    record("visitor", "GET /admin/", "denied (redirect to /login)", f"HTTP {r.status}", "login_required")
    assert r.status == 302 and "/login" in r.headers["location"]


def test_visitor_cannot_confirm_a_team(world, visitor):
    tid, team = pending_setup(world)
    r = visitor.post(f"/admin/tournament/{tid}/team/{team}/confirm", max_redirects=0)
    record("visitor", "POST .../team/<id>/confirm", "denied and team still pending",
           f"HTTP {r.status}; team confirmed = {world.team_row(team)[1]}", "database read after the request")
    assert r.status in DENIED and world.team_row(team) == ("Pending Co", False, False)


def test_visitor_cannot_add_a_team_by_hand(world, visitor):
    tid = world.tournament()
    r = visitor.post(f"/admin/tournament/{tid}/team/add", data={"name": "Sneaky", "player1": "a", "player2": "b"},
                     max_redirects=0)
    record("visitor", "POST .../team/add", "denied and no team created",
           f"HTTP {r.status}; teams = {len(world.teams(tid))}", "database read after the request")
    assert r.status in DENIED and world.teams(tid) == []


def test_public_form_post_without_a_csrf_token_is_refused(world, visitor):
    tid = world.tournament()
    r = visitor.post("/register/team", form={"code": "REG001", "team_name": "NoToken", "player1": "a", "player2": "b"},
                     max_redirects=0)
    CONTROLS.append(["CSRF on the public registration form", f"HTTP {r.status} without token",
                     "Flask-WTF CSRFProtect (app/__init__.py line 9); form carries a csrf_token field"])
    assert r.status == 400 and world.teams(tid) == []


def test_json_api_accepts_a_registration_without_any_token(world, visitor):
    """Observation for DR-12: the API blueprint is CSRF-exempt and has no rate limit."""
    tid = world.tournament()
    r = visitor.post("/api/register/team", data={"code": "REG001", "team_name": "ApiTeam", "player1": "a", "player2": "b"})
    CONTROLS.append(["CSRF on /api/register/team", f"HTTP {r.status}: accepted without a token (DR-12)",
                     "csrf.exempt(api) in app/__init__.py"])
    assert r.status == 200 and [t[0] for t in world.teams(tid)] == ["ApiTeam"]


# ---- admin ------------------------------------------------------------------------------

def test_admin_can_open_the_registrations_page(world, page):
    tid = world.tournament()
    admin_login(page)
    r = page.request.get(f"/admin/tournament/{tid}/registrations")
    record("admin", f"GET /admin/tournament/{tid}/registrations", "allowed (200)", f"HTTP {r.status}", "response status")
    assert r.status == 200


def test_admin_can_confirm_a_team_with_a_csrf_token(world, page):
    tid, team = pending_setup(world)
    admin_login(page)
    page.goto(f"/admin/tournament/{tid}/registrations")
    token = page.locator("meta[name=csrf-token]").get_attribute("content")
    r = page.request.post(f"/admin/tournament/{tid}/team/{team}/confirm", headers={"X-CSRFToken": token})
    record("admin", "POST .../team/<id>/confirm with CSRF token", "allowed and team confirmed",
           f"HTTP {r.status}; confirmed = {world.team_row(team)[1]}", "database read after the request")
    assert r.status == 200 and world.team_row(team)[1] is True


def test_admin_confirm_without_a_csrf_token_is_refused(world, page):
    tid, team = pending_setup(world)
    admin_login(page)
    r = page.request.post(f"/admin/tournament/{tid}/team/{team}/confirm", max_redirects=0)
    record("admin", "POST .../team/<id>/confirm WITHOUT CSRF token", "denied and team still pending",
           f"HTTP {r.status}; confirmed = {world.team_row(team)[1]}", "database read after the request")
    assert r.status == 400 and world.team_row(team)[1] is False


# ---- observed controls ------------------------------------------------------------------

def test_session_cookie_attributes(world, page):
    world.tournament()
    admin_login(page)
    cookie = next(c for c in page.context.cookies() if c["name"] == "session")
    CONTROLS.append(["Session cookie attributes",
                     f"HttpOnly={cookie['httpOnly']}, Secure={cookie['secure']}, SameSite={cookie.get('sameSite')}",
                     "config.py sets no SESSION_COOKIE_* values, so Flask defaults apply"])
    assert cookie["httpOnly"] is True


def test_security_response_headers_are_recorded(world, visitor):
    world.tournament()
    r = visitor.get("/login")
    wanted = ["content-security-policy", "x-frame-options", "x-content-type-options",
              "strict-transport-security", "referrer-policy"]
    seen = {h: r.headers.get(h) for h in wanted}
    CONTROLS.append(["Security headers on /login",
                     "; ".join(f"{h}: {v or 'MISSING'}" for h, v in seen.items()),
                     "no after_request hook or header library found in app/"])
    assert r.status == 200


def test_password_is_not_visible_in_the_login_form_get(world, page):
    page.goto("/login")
    expect(page.locator("input[name=password]")).to_have_attribute("type", "password")
    CONTROLS.append(["Login password field", "type=password", "templates/auth/login.html"])
