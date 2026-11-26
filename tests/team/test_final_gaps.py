"""Last reachable gaps from the 2026-11-26 coverage run: the app factory when an admin already
exists, and the Socket.IO score event with only one score.
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest

from app import create_app, db, socketio
from app.models import Admin
from team_support import make_tournament
from team_support_more import make_match, make_teams
from test_socket_utils_models import socket_handlers  # noqa: F401  (re-used fixture)


def test_create_app_does_not_add_a_second_default_admin(tmp_path):
    class FileConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'factory.db').as_posix()}"
        SECRET_KEY = "x"
        WTF_CSRF_ENABLED = False

    first = create_app(FileConfig)
    second = create_app(FileConfig)          # same database file: the default admin already exists
    with second.app_context():
        assert Admin.query.count() == 1 and Admin.query.one().username == "admin"
        db.session.remove()
        db.engine.dispose()
    with first.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.mark.usefixtures("socket_handlers")
def test_update_score_event_with_only_team1_score_leaves_team2_alone(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b, score2=3)
    admin_io = socketio.test_client(app, flask_test_client=authenticated_client)
    admin_io.emit("update_score", {"match_id": m.id, "team1_score": 6})
    db.session.expire_all()
    assert (m.team1_score, m.team2_score) == (6, 3)
    admin_io.disconnect()
