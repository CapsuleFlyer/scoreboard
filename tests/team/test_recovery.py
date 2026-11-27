"""Failure-and-recovery tests (brief section 5): a state-changing operation meets a database that
becomes unavailable before the write completes, then the database comes back and the operation is
retried.

Test double: FlakyCommit replaces db.session.commit. While `down` is True it rolls the session back
(what SQLAlchemy does when a flush fails) and raises OperationalError, so nothing is written. Setting
`down = False` restores the dependency.

Each test checks, in order: the failure, the persisted state after it (no row, shared count
unchanged), the retry, the final state, and that repeating the request creates no duplicate.
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest
from sqlalchemy.exc import OperationalError

from app import db
from team_support import CODE, make_team, make_tournament, names, reload_team

REGISTER = "/api/register/team"


class FlakyCommit:
    def __init__(self, session):
        self.session = session
        self.real_commit = session.commit
        self.down = False
        self.failures = 0

    def __call__(self):
        if self.down:
            self.failures += 1
            self.session.rollback()
            raise OperationalError("COMMIT", {}, Exception("database is unavailable"))
        return self.real_commit()


@pytest.fixture
def flaky(monkeypatch):
    double = FlakyCommit(db.session)
    monkeypatch.setattr(db.session, "commit", double)
    return double


def body(**fields):
    data = {"code": CODE, "team_name": "Alpha", "player1": "Ann", "player2": "Bob"}
    data.update(fields)
    return data


def test_registration_recovers_after_the_database_comes_back(app, client, flaky):
    app.config["PROPAGATE_EXCEPTIONS"] = False          # a crash must show as a response, not an exception
    t = make_tournament(max_teams=3)

    flaky.down = True                                   # dependency unavailable before the write completes
    failed = client.post(REGISTER, json=body())
    assert failed.status_code == 500 and flaky.failures == 1
    assert names(t) == [] and t.get_registered_team_count() == 0       # persisted state after the failure

    flaky.down = False                                  # dependency restored
    retry = client.post(REGISTER, json=body())
    assert retry.status_code == 200 and names(t) == ["Alpha"]          # final state after the retry
    assert t.get_registered_team_count() == 1

    again = client.post(REGISTER, json=body())          # repeating the request must not duplicate
    assert again.status_code == 400 and names(t) == ["Alpha"] and t.get_registered_team_count() == 1


def test_admin_confirmation_recovers_after_the_database_comes_back(app, authenticated_client, flaky):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    t = make_tournament(require_confirmation=True)
    team = make_team(t, "Pending Co", confirmed=False)
    url = f"/admin/tournament/{t.id}/team/{team.id}/confirm"

    flaky.down = True
    assert authenticated_client.post(url).status_code == 500 and flaky.failures == 1
    assert reload_team(team.id).is_confirmed is False                  # state unchanged by the failed write

    flaky.down = False
    assert authenticated_client.post(url).status_code == 200
    assert reload_team(team.id).is_confirmed is True

    assert authenticated_client.post(url).status_code == 200           # repeat: still one confirmed team
    assert names(t) == ["Pending Co"] and reload_team(team.id).is_confirmed is True


@pytest.mark.xfail(strict=True, reason="DR-22 (READ): a database failure is answered with the default HTML 500 page, not a JSON error, so API clients cannot tell what happened")
def test_api_reports_a_database_outage_as_a_json_error(app, client, flaky):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    make_tournament()
    flaky.down = True
    r = client.post(REGISTER, json=body())
    assert r.status_code in (500, 503) and r.is_json
