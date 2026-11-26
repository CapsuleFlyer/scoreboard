"""Tests that close the gaps the first whole-app coverage run showed (bracket guards and byes,
standings branches, dangling next-match ids, the winner team on the display state).

Code that cannot be reached is NOT tested; it is listed in docs/whole-app-coverage.md:
  bracket.py 84-92   team2 present and team1 missing in round 1 (byes are padded at the end)
  bracket.py 174->172, 183->182, 187, 190->195   double elimination branches no team count can reach
  bracket.py 237->exit, 315->exit, 363->exit    "no first match" checks after matches were just created
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest

from app import db
from app.blueprints.admin import calculate_standings
from app.blueprints.bracket import (create_double_elimination_bracket, create_round_robin,
                                    create_round_robin_playoffs, create_single_elimination_bracket,
                                    create_swiss_round)
from app.models import DisplayState, Match
from team_support import make_tournament
from team_support_more import bearer, make_match, make_teams, make_token

BUILDERS = [create_single_elimination_bracket, create_double_elimination_bracket, create_round_robin,
            create_round_robin_playoffs, create_swiss_round]


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda f: f.__name__)
@pytest.mark.parametrize("count", [0, 1])
def test_bracket_builders_do_nothing_below_two_teams(app, builder, count):
    t = make_tournament()
    teams = make_teams(t, count)
    builder(t.id, [x.id for x in teams])
    assert Match.query.filter_by(tournament_id=t.id).count() == 0


def test_single_elimination_with_five_teams_gives_byes_and_advances_the_bye_winner(app):
    t = make_tournament()
    teams = make_teams(t, 5)
    create_single_elimination_bracket(t.id, [x.id for x in teams])
    rounds = {r: Match.query.filter_by(tournament_id=t.id, round_number=r).count() for r in (1, 2, 3)}
    assert rounds == {1: 4, 2: 2, 3: 1}
    bye = Match.query.filter_by(tournament_id=t.id, round_number=1, match_number=3).one()
    empty = Match.query.filter_by(tournament_id=t.id, round_number=1, match_number=4).one()
    assert bye.is_completed and bye.winner_id == bye.team1_id and bye.team2_id is None
    assert empty.is_completed and empty.winner_id is None            # both slots empty: closed, no winner
    next_match = db.session.get(Match, bye.next_match_id)
    assert next_match.team1_id == bye.winner_id                      # odd match number feeds team 1
    assert Match.query.filter_by(tournament_id=t.id, is_current=True).count() == 1


def test_single_elimination_with_three_teams_feeds_team2_from_an_even_match(app):
    t = make_tournament()
    teams = make_teams(t, 3)
    create_single_elimination_bracket(t.id, [str(x.id) for x in teams])      # ids may arrive as strings
    bye = Match.query.filter_by(tournament_id=t.id, round_number=1, match_number=2).one()
    assert db.session.get(Match, bye.next_match_id).team2_id == bye.winner_id


# ---- standings branches -----------------------------------------------------------------

def test_calculate_standings_team2_winner_and_missing_team1(app):
    t = make_tournament(format="round_robin")
    a, b, c = make_teams(t, 3)
    make_match(t, 1, 1, a, b, 1, 4, is_completed=True, winner_id=b.id)       # team 1 loses, team 2 wins
    make_match(t, 1, 2, None, c, 0, 2, is_completed=True, winner_id=c.id)    # no team 1 at all
    table = calculate_standings(t.id)
    assert [r["team_id"] for r in table] == [b.id, c.id, a.id]
    assert (table[2]["wins"], table[2]["losses"]) == (0, 1)
    assert (table[1]["points_for"], table[1]["points_against"]) == (2, 0)


# ---- next match id that points nowhere --------------------------------------------------

def test_api_complete_with_a_dangling_next_match_id(app, authenticated_client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b, next_match_id=9999)
    r = authenticated_client.post(f"/api/match/{m.id}/complete", json={"winner_id": a.id})
    assert r.status_code == 200 and r.get_json()["is_completed"] is True


def test_external_set_winner_with_a_dangling_next_match_id(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b, score1=2, score2=0, next_match_id=9999)
    _, raw = make_token()
    r = client.post(f"/ext/v1/match/{m.id}/set-winner", json={}, headers=bearer(raw))
    assert r.get_json()["success"] is True and r.get_json()["winner_id"] == a.id


@pytest.mark.parametrize("next_id", [None, 9999])
def test_external_complete_without_a_usable_next_match(app, client, next_id):
    t = make_tournament()
    a, b = make_teams(t, 2)
    m = make_match(t, team1=a, team2=b, next_match_id=next_id)
    _, raw = make_token()
    r = client.post(f"/ext/v1/match/{m.id}/complete", json={"winner_id": b.id}, headers=bearer(raw))
    assert r.get_json()["success"] is True
    db.session.expire_all()
    assert m.winner_id == b.id and m.is_completed is True


# ---- winner team on the display state ---------------------------------------------------

def test_display_state_includes_the_winner_team_carried_by_the_state_object(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    state = DisplayState(mode="winner")
    db.session.add(state)
    db.session.commit()
    state.winner_team_id = a.id          # not a column: it lives only on this object (see DR-20)
    assert client.get("/api/display/state").get_json()["winner_team"]["id"] == a.id
    state.winner_team_id = 99999         # unknown team: no winner_team key
    assert "winner_team" not in client.get("/api/display/state").get_json()


@pytest.mark.xfail(strict=True, reason="DR-20 (READ): winner_team_id is not a DisplayState column, so it is lost once the object is reloaded")
def test_display_mode_winner_team_is_persisted(app, client):
    t = make_tournament()
    a, b = make_teams(t, 2)
    client.post("/api/display/mode", json={"mode": "winner", "winner_team_id": a.id})
    db.session.expunge_all()
    assert "winner_team" in client.get("/api/display/state").get_json()
