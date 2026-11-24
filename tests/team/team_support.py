"""Small helpers shared by the tests in tests/team (kept out of conftest.py on purpose:
conftest.py belongs to upstream, this file belongs to the team)."""
from app import db
from app.models import Team, Tournament

CODE = "REG001"


def make_tournament(**fields):
    values = dict(name="Reg Test", registration_code=CODE, max_teams=16)
    values.update(fields)
    t = Tournament(**values)
    db.session.add(t)
    db.session.commit()
    return t


def make_team(tournament, name="Alpha", confirmed=True, checked_in=False):
    team = Team(name=name, player1="Ann", player2="Bob", tournament_id=tournament.id,
                is_confirmed=confirmed, is_checked_in=checked_in)
    db.session.add(team)
    db.session.commit()
    return team


def names(tournament):
    return sorted(t.name for t in Team.query.filter_by(tournament_id=tournament.id).all())


def reload_team(team_id):
    """Fresh read of a team row (None if it was deleted)."""
    db.session.expire_all()
    return db.session.get(Team, team_id)
