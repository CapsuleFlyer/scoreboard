"""White-box unit tests for Tournament.can_register() (app/models.py).

Business rule 2 (docs/test-basis.md): registration is allowed only if
  registration_open AND status == 'registration' AND deadline not passed AND count < max_teams.
The checks run in that order and the first failing check decides the message.

Most tests use a transient Tournament (never saved to the database) with the team count
stubbed, so each condition can be controlled on its own. A few tests use the real database.
"""
from datetime import datetime, timedelta, timezone

import pytest

import app.models as models
from app import db
from app.models import Team, Tournament

NOW = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)

OK = (True, "OK")
CLOSED = (False, "Registration is closed")
STARTED = (False, "Tournament has already started")
DEADLINE = (False, "Registration deadline has passed")
FULL = (False, "Tournament is full")


def make_tournament(monkeypatch, registered=0, **fields):
    """A transient Tournament with all the fields can_register() reads set explicitly."""
    values = dict(
        registration_open=True,
        status="registration",
        registration_deadline=None,
        max_teams=16,
    )
    values.update(fields)
    t = Tournament(name="T", registration_code="T00001", **values)
    monkeypatch.setattr(Tournament, "get_registered_team_count", lambda self: registered)
    return t


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    """Freeze utc_now() so deadline tests are exact."""
    monkeypatch.setattr(models, "utc_now", lambda: NOW)


# ---- Decision table: one condition fails at a time (MC/DC style) -----------------------

def test_all_conditions_pass(monkeypatch):
    assert make_tournament(monkeypatch).can_register() == OK


def test_closed_registration_is_refused(monkeypatch):
    assert make_tournament(monkeypatch, registration_open=False).can_register() == CLOSED


@pytest.mark.parametrize("status", ["ready", "in_progress", "completed", "cancelled"])
def test_status_other_than_registration_is_refused(monkeypatch, status):
    assert make_tournament(monkeypatch, status=status).can_register() == STARTED


def test_deadline_in_the_past_is_refused(monkeypatch):
    t = make_tournament(monkeypatch, registration_deadline=NOW - timedelta(days=1))
    assert t.can_register() == DEADLINE


def test_deadline_in_the_future_is_allowed(monkeypatch):
    t = make_tournament(monkeypatch, registration_deadline=NOW + timedelta(days=1))
    assert t.can_register() == OK


def test_full_tournament_is_refused(monkeypatch):
    assert make_tournament(monkeypatch, registered=16, max_teams=16).can_register() == FULL


# ---- Boundary value analysis ----------------------------------------------------------

@pytest.mark.parametrize(
    "registered, expected",
    [(2, OK), (3, OK), (4, FULL), (5, FULL)],
    ids=["two_below", "just_below", "at_limit", "just_above"],
)
def test_capacity_boundary(monkeypatch, registered, expected):
    assert make_tournament(monkeypatch, registered=registered, max_teams=4).can_register() == expected


def test_capacity_of_one(monkeypatch):
    assert make_tournament(monkeypatch, registered=0, max_teams=1).can_register() == OK
    assert make_tournament(monkeypatch, registered=1, max_teams=1).can_register() == FULL


@pytest.mark.parametrize(
    "offset, expected",
    [(timedelta(microseconds=-1), DEADLINE), (timedelta(0), OK), (timedelta(microseconds=1), OK)],
    ids=["just_after_deadline", "exactly_at_deadline", "just_before_deadline"],
)
def test_deadline_boundary(monkeypatch, offset, expected):
    # deadline = NOW + offset, so a negative offset puts the deadline in the past
    t = make_tournament(monkeypatch, registration_deadline=NOW + offset)
    assert t.can_register() == expected


# ---- Order of the checks (first failing condition decides the message) -----------------

def test_closed_wins_over_started(monkeypatch):
    t = make_tournament(monkeypatch, registration_open=False, status="in_progress")
    assert t.can_register() == CLOSED


def test_started_wins_over_deadline(monkeypatch):
    t = make_tournament(monkeypatch, status="in_progress", registration_deadline=NOW - timedelta(days=1))
    assert t.can_register() == STARTED


def test_deadline_wins_over_full(monkeypatch):
    t = make_tournament(
        monkeypatch, registered=16, max_teams=16, registration_deadline=NOW - timedelta(days=1)
    )
    assert t.can_register() == DEADLINE


# ---- Real database: how the count behaves (assumption A4, defect DR-08) ----------------

def test_pending_team_counts_toward_the_cap(app):
    t = Tournament(name="Cap", registration_code="CAP001", max_teams=1, require_confirmation=True)
    db.session.add(t)
    db.session.commit()
    assert t.can_register() == OK

    db.session.add(Team(name="Pending", player1="", player2="", tournament_id=t.id, is_confirmed=False))
    db.session.commit()

    assert t.get_registered_team_count() == 1
    assert t.get_confirmed_team_count() == 0
    assert t.can_register() == FULL


# ---- Known defect DR-03: documented with a strict xfail --------------------------------

@pytest.mark.xfail(strict=True, reason="DR-03: SQLite returns a naive datetime, so comparing it with utc_now() raises TypeError")
def test_deadline_survives_a_database_reload(app, monkeypatch):
    # Not frozen here: use the real clock path through the database.
    monkeypatch.undo()
    t = Tournament(
        name="Deadline",
        registration_code="DL0001",
        registration_deadline=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.session.add(t)
    db.session.commit()
    db.session.expire_all()

    assert t.can_register() == DEADLINE
