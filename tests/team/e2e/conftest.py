"""Fixtures for the browser tests: a real server on a throw-away SQLite file with CSRF switched
ON (so the forms use real tokens), a seeded database per test, and a Chromium page.

These tests are skipped (not collected) when Playwright is not installed, so the normal unit-test
run and the CI gate are unaffected. To skip them on a machine that has Playwright:
    python -m pytest tests/team --ignore=tests/team/e2e
Status: written against the templates (READ). Run on your machine before citing any result.
"""
import os
import threading
from pathlib import Path

import pytest

try:
    import playwright  # noqa: F401
except ImportError:                                   # pragma: no cover
    collect_ignore_glob = ["test_*.py"]

import werkzeug.serving  # noqa: F401  (create_app picks the threading async mode when it is loaded)
from werkzeug.serving import make_server

from app import create_app, db
from app.models import Admin, Team, Tournament

from e2e_helpers import ADMIN_PASSWORD, ADMIN_USER, EVIDENCE  # noqa: E402


class World:
    """Seeds and reads the database of the running server (returns plain values, not rows)."""

    def __init__(self, app, url):
        self.app, self.url = app, url

    def tournament(self, **fields):
        values = dict(name="Spring Cup", registration_code="REG001", max_teams=16)
        values.update(fields)
        with self.app.app_context():
            t = Tournament(**values)
            db.session.add(t)
            db.session.commit()
            return t.id

    def team(self, tournament_id, name="Alpha", confirmed=True, checked_in=False):
        with self.app.app_context():
            t = Team(name=name, player1="Ann", player2="Bob", tournament_id=tournament_id,
                     is_confirmed=confirmed, is_checked_in=checked_in)
            db.session.add(t)
            db.session.commit()
            return t.id

    def teams(self, tournament_id):
        """[(name, confirmed, checked_in)] in id order."""
        with self.app.app_context():
            rows = Team.query.filter_by(tournament_id=tournament_id).order_by(Team.id).all()
            return [(r.name, r.is_confirmed, r.is_checked_in) for r in rows]

    def team_row(self, team_id):
        with self.app.app_context():
            t = db.session.get(Team, team_id)
            return None if t is None else (t.name, t.is_confirmed, t.is_checked_in)


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("e2e") / "e2e.db"

    class E2EConfig:
        SECRET_KEY = "e2e-secret-key"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file.as_posix()}"
        WTF_CSRF_ENABLED = True          # real CSRF tokens, as in production

    app = create_app(E2EConfig)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app.e2e_url = f"http://127.0.0.1:{server.server_port}"
    yield app
    server.shutdown()
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def world(live_server):
    app = live_server
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = Admin(username=ADMIN_USER)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
    return World(app, app.e2e_url)


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    options = {}
    proxy = os.environ.get("E2E_PROXY")          # e.g. http://127.0.0.1:8090 to pass traffic through OWASP ZAP
    if proxy:
        # Chromium does not proxy loopback addresses unless told to
        options = {"proxy": {"server": proxy}, "args": ["--proxy-bypass-list=<-loopback>"]}
    with sync_playwright() as p:
        b = p.chromium.launch(**options)
        yield b
        b.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, "rep_" + call.when, outcome.get_result())


@pytest.fixture
def page(browser, world, request):
    ctx = browser.new_context(base_url=world.url, viewport={"width": 1280, "height": 900})
    ctx.set_default_timeout(10_000)
    pg = ctx.new_page()
    yield pg
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(EVIDENCE / f"FAILED_{request.node.name}.png"))
    ctx.close()


@pytest.fixture
def shot(page, request):
    """shot("step name") saves a screenshot under docs/evidence/e2e/screens when E2E_SHOTS=1."""
    def take(label="final"):
        if os.environ.get("E2E_SHOTS") == "1":
            folder = EVIDENCE / "screens"
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / f"{request.node.name}__{label}.png"), full_page=True)
    return take

