"""Whole-app tests: Socket.IO events (socket_events.py), app/utils.py and app/models.py leftovers.
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest

from app import db, socketio
from app.models import Admin, APIToken, DisplayState, Match, Team, Tournament, TVSession
from app import models as models_module
from app.utils import (THEMES, generate_theme_css, get_all_themes, get_theme, sanitize_message,
                       sanitize_text)
from team_support import make_tournament
from team_support_more import make_match, make_teams, make_token, make_tv


@pytest.fixture
def socket_handlers(app):
    """The tests build a new app (and a new Socket.IO server) every time, but the @socketio.on
    handlers are only registered when socket_events is first imported, so only the first server
    would have them. Re-run the decorators against the current server. Production builds one app,
    so it is not affected."""
    import importlib
    from app.blueprints import socket_events
    importlib.reload(socket_events)


def received(sio, name):
    return [e["args"][0] for e in sio.get_received() if e["name"] == name]


# ---- socket events ----------------------------------------------------------------------

@pytest.mark.usefixtures("socket_handlers")
def test_connect_and_disconnect(app, client):
    sio = socketio.test_client(app, flask_test_client=client)
    assert sio.is_connected()
    sio.disconnect()
    assert not sio.is_connected()


@pytest.mark.usefixtures("socket_handlers")
def test_join_tv_refreshes_last_seen_for_a_known_code_only(app, client):
    from datetime import datetime, timedelta
    tv = make_tv("ABC234", last_seen=datetime.utcnow() - timedelta(hours=1))
    before = tv.last_seen
    sio = socketio.test_client(app, flask_test_client=client)
    sio.emit("join_tv", {"code": "abc234"})
    db.session.expire_all()
    assert TVSession.query.one().last_seen > before
    sio.emit("join_tv", {"code": "NOPE99"})          # unknown code: joins the room, changes nothing
    sio.emit("join_tv", {})                          # no code: ignored
    sio.disconnect()


@pytest.mark.usefixtures("socket_handlers")
def test_leave_tv_and_join_tournament(app, client):
    sio = socketio.test_client(app, flask_test_client=client)
    sio.emit("leave_tv", {"code": "abc234"})
    sio.emit("leave_tv", {})
    sio.get_received()
    sio.emit("join_tournament", {"tournament_id": 7})
    assert received(sio, "joined") == [{"room": "tournament_7"}]
    sio.disconnect()


@pytest.mark.usefixtures("socket_handlers")
def test_admin_events_are_broadcast_and_anonymous_ones_are_ignored(app, authenticated_client):
    anon_flask = app.test_client()
    admin_io = socketio.test_client(app, flask_test_client=authenticated_client)
    anon_io = socketio.test_client(app, flask_test_client=anon_flask)
    watcher = socketio.test_client(app)
    for s in (admin_io, anon_io, watcher):
        s.get_received()
    admin_io.emit("start_countdown", {"tournament_id": 1})
    assert received(watcher, "start_countdown") == [{"tournament_id": 1}]
    anon_io.emit("start_countdown", {"tournament_id": 2})
    assert received(watcher, "start_countdown") == []


@pytest.mark.usefixtures("socket_handlers")
def test_update_score_event_saves_and_broadcasts(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b)
    admin_io = socketio.test_client(app, flask_test_client=authenticated_client)
    watcher = socketio.test_client(app)
    watcher.get_received()
    admin_io.emit("update_score", {"match_id": m.id, "team1_score": 4, "team2_score": 2})
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (4, 2)
    assert received(watcher, "score_update") == [{"match_id": m.id, "team1_score": 4, "team2_score": 2}]
    admin_io.emit("update_score", {"match_id": m.id, "team2_score": 9})          # one key only
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (4, 9)
    watcher.get_received()
    admin_io.emit("update_score", {"match_id": 9999, "team1_score": 1})          # unknown match
    assert received(watcher, "score_update") == []


@pytest.mark.usefixtures("socket_handlers")
def test_update_score_from_an_anonymous_socket_changes_nothing(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b)
    anon = socketio.test_client(app, flask_test_client=client)
    anon.emit("update_score", {"match_id": m.id, "team1_score": 99})
    db.session.expire_all()
    assert m.team1_score == 0


@pytest.mark.usefixtures("socket_handlers")
def test_winner_pending_event(app, authenticated_client):
    admin_io = socketio.test_client(app, flask_test_client=authenticated_client)
    watcher = socketio.test_client(app)
    watcher.get_received()
    payload = {"match_id": 1, "team1_score": 3, "team2_score": 3, "winner_id": 5, "winner_name": "X"}
    admin_io.emit("winner_pending", payload)
    assert received(watcher, "winner_pending") == [dict(payload, is_overtime=False)]
    admin_io.emit("winner_pending", dict(payload, is_overtime=True))
    assert received(watcher, "winner_pending")[0]["is_overtime"] is True


@pytest.mark.usefixtures("socket_handlers")
def test_tv_command_and_refresh_reach_only_that_tvs_room(app, authenticated_client):
    admin_io = socketio.test_client(app, flask_test_client=authenticated_client)
    tv = socketio.test_client(app)
    other = socketio.test_client(app)
    tv.emit("join_tv", {"code": "ABC234"})
    other.emit("join_tv", {"code": "ZZZ999"})
    for s in (admin_io, tv, other):
        s.get_received()
    admin_io.emit("tv_command", {"tv_code": "abc234", "command": {"mode": "bracket"}})
    admin_io.emit("refresh_tv", {"tv_code": "abc234"})
    admin_io.emit("tv_command", {"command": {}})            # no code: ignored
    admin_io.emit("refresh_tv", {})                         # no code: ignored
    tv_events = tv.get_received()
    assert [e["args"][0] for e in tv_events if e["name"] == "display_update"] == [{"mode": "bracket"}]
    assert [e["name"] for e in tv_events].count("refresh_display") == 1
    assert received(other, "display_update") == [] and received(other, "refresh_display") == []


# ---- utils ------------------------------------------------------------------------------

@pytest.mark.parametrize("raw,kwargs,expected", [
    (None, {}, ""),
    ("  hi  ", {}, "hi"),
    ("x" * 150, {}, "x" * 100),
    ("x" * 150, {"max_length": 10}, "x" * 10),
    ("x" * 150, {"max_length": None}, "x" * 150),
    ("a\x00b\x07c", {}, "abc"),
    ("tab\tnew\nline", {}, "tab\tnew\nline"),
    ("<b>\"hi\"</b>", {}, "&lt;b&gt;&quot;hi&quot;&lt;/b&gt;"),
    (42, {}, "42"),
])
def test_sanitize_text(raw, kwargs, expected):
    assert sanitize_text(raw, **kwargs) == expected


@pytest.mark.parametrize("raw,expected", [
    (None, ""), ("  hi  ", "hi"), ("m" * 600, "m" * 500), ("<i>x</i>", "&lt;i&gt;x&lt;/i&gt;"), (7, "7"),
])
def test_sanitize_message(raw, expected):
    assert sanitize_message(raw) == expected


def test_theme_helpers():
    assert get_theme("dark-orange") is THEMES["dark-orange"]
    assert get_theme("nope") is THEMES["dark-orange"]
    assert get_all_themes() is THEMES


@pytest.mark.parametrize("theme_id", list(THEMES))
def test_every_theme_generates_css_with_its_primary_colour(theme_id):
    css = generate_theme_css(theme_id)
    assert "--ru-primary: " + THEMES[theme_id]["primary"] in css


def test_unknown_theme_css_falls_back_to_the_default():
    assert generate_theme_css("nope") == generate_theme_css("dark-orange")


# ---- models -----------------------------------------------------------------------------

def test_admin_password_handling_and_dict(app):
    a = Admin(username="x")
    assert a.check_password("anything") is False            # no hash yet
    a.set_password("pw")
    assert a.check_password("pw") and not a.check_password("other") and a.password_hash != "pw"
    db.session.add(a)
    db.session.commit()
    d = a.to_dict()
    assert d["username"] == "x" and d["is_active"] is True and d["created_at"] is not None
    assert Admin(username="y").to_dict()["created_at"] is None


def _force_codes(monkeypatch, letters):
    seq = iter(letters)
    monkeypatch.setattr(models_module.secrets, "choice", lambda chars: next(seq))


def test_tv_code_generation_skips_a_code_already_in_use(app, monkeypatch):
    make_tv("AAAAAA")
    _force_codes(monkeypatch, "AAAAAA" + "BBBBBB")
    assert TVSession.generate_code() == "BBBBBB"


def test_tv_code_alphabet_excludes_confusing_characters(app):
    for _ in range(30):
        code = TVSession.generate_code()
        assert len(code) == 6 and not set(code) & set("O0I1L")


def test_registration_code_generation_skips_a_code_already_in_use(app, monkeypatch):
    make_tournament(registration_code="AAAAAA")
    _force_codes(monkeypatch, "AAAAAA" + "CCCCCC")
    assert Tournament.generate_registration_code() == "CCCCCC"


def test_dict_exports(app):
    t = make_tournament(name="Dicts")
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b, is_completed=True, winner_id=a.id)
    assert t.to_dict()["id"] == t.id and t.to_dict()["name"] == "Dicts"
    d = m.to_dict()
    assert d["winner"]["id"] == a.id and d["team1"]["id"] == a.id and d["is_completed"] is True
    assert make_match(t, 2, 1).to_dict()["winner"] is None
    tv = make_tv("ABC234")
    assert tv.to_dict()["code"] == "ABC234" and tv.to_dict()["id"] == tv.id
    assert DisplayState(mode="waiting").to_dict() == {
        "mode": "waiting", "tournament_id": None, "match_id": None, "custom_message": None, "show_players": None}


def test_api_token_helpers(app):
    token, raw = make_token(permissions=["team:read"])
    assert token.has_permission("team:read") and not token.has_permission("match:write")
    assert token.get_permissions() == ["team:read"]
    token.permissions = "not json"
    assert token.get_permissions() == [] and token.has_permission("team:read") is False
    token.permissions = None
    assert token.get_permissions() == [] and token.has_permission("team:read") is False
    default, _ = make_token()
    assert default.get_permissions() == APIToken.SCOPES
    d = default.to_dict()
    assert d["admin_username"] == "admin" and d["last_used"] is None and d["expires_at"] is None


def test_api_token_validation(app):
    token, raw = make_token()
    assert APIToken.validate_token(raw).id == token.id
    assert token.request_count == 1 and token.last_used is not None
    assert APIToken.validate_token("wrong") is None
    token.is_active = False
    db.session.commit()
    assert APIToken.validate_token(raw) is None
    hash_a_first = APIToken.hash_token("a")
    hash_a_second = APIToken.hash_token("a")
    hash_b = APIToken.hash_token("b")

    assert hash_a_first == hash_a_second
    assert hash_a_first != hash_b
    token_a = APIToken.generate_token()
    token_b = APIToken.generate_token()

    assert token_a != token_b
