"""More helpers for the whole-app tests (see team_support.py for the first set)."""
from app import db
from app.models import APIToken, Match, Team, TVSession


def make_match(tournament, round_number=1, match_number=1, team1=None, team2=None,
               score1=0, score2=0, **fields):
    m = Match(tournament_id=tournament.id, round_number=round_number, match_number=match_number,
              team1_id=team1.id if team1 else None, team2_id=team2.id if team2 else None,
              team1_score=score1, team2_score=score2, **fields)
    db.session.add(m)
    db.session.commit()
    return m


def make_global_team(name="Loose", p1="Ann", p2="Bob"):
    t = Team(name=name, player1=p1, player2=p2)
    db.session.add(t)
    db.session.commit()
    return t


def make_teams(tournament, count, confirmed=True):
    out = []
    for i in range(count):
        t = Team(name=f"T{i + 1}", player1=f"P{i + 1}a", player2=f"P{i + 1}b",
                 tournament_id=tournament.id, is_confirmed=confirmed)
        db.session.add(t)
        out.append(t)
    db.session.commit()
    return out


def make_tv(code="ABC234", **fields):
    tv = TVSession(code=code, **fields)
    db.session.add(tv)
    db.session.commit()
    return tv


def make_token(permissions=None, admin_id=1, tournament_id=None, expires_at=None, active=True, name="t"):
    """Return (token row, raw token string)."""
    token, raw = APIToken.create_token(name=name, admin_id=admin_id, permissions=permissions,
                                       tournament_id=tournament_id, expires_at=expires_at)
    token.is_active = active
    db.session.add(token)
    db.session.commit()
    return token, raw


def bearer(raw):
    return {"Authorization": f"Bearer {raw}"}


def flashes(client):
    """Flash messages waiting in the session (not yet rendered)."""
    with client.session_transaction() as sess:
        return [m for _, m in sess.get("_flashes", [])]
