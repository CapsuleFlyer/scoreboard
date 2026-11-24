"""Unit tests for the remaining in-scope helpers: sanitize_team_name, sanitize_player_name
(app/utils.py), login_required (app/blueprints/auth.py), Team.to_dict and
Tournament.to_public_dict (app/models.py).
Status: written against the source (READ). Run on your machine before citing any result.
"""
import pytest
from flask import Blueprint

from app.blueprints.auth import login_required
from app.utils import sanitize_player_name, sanitize_team_name
from team_support import make_team, make_tournament


# ---- sanitize_team_name: boundary is 8 characters today (DR-05: intended rule is 20) ----

@pytest.mark.parametrize("raw,expected", [
    (None, ""),                       # None branch
    ("", ""),
    ("   ", ""),
    ("A" * 7, "A" * 7),               # just below the 8-character cut
    ("A" * 8, "A" * 8),               # exactly at
    ("A" * 9, "A" * 8),               # just above is truncated
    ("  Bot  ", "Bot"),
    ("a   b", "a b"),                 # runs of spaces collapse
    ("a<b>c", "abc"),                 # unsafe characters removed
    ("R&D!", "R&amp;D!"),             # allowed '&' is HTML-escaped afterwards
    ("it's", "it&#x27;s"),            # apostrophe allowed then escaped
    (12345, "12345"),                 # non-string input is converted
])
def test_sanitize_team_name(raw, expected):
    assert sanitize_team_name(raw) == expected


# ---- sanitize_player_name: boundary is 10 characters today -----------------------------

@pytest.mark.parametrize("raw,expected", [
    (None, ""),
    ("", ""),
    ("B" * 9, "B" * 9),
    ("B" * 10, "B" * 10),
    ("B" * 11, "B" * 10),
    ("Ann   Lee", "Ann Lee"),
    ("a<b>c", "abc"),
    ("R&D", "RD"),                    # '&' is NOT allowed in player names (differs from team names)
    ("o'neil", "oneil"),              # apostrophe not allowed either
    (987, "987"),
])
def test_sanitize_player_name(raw, expected):
    assert sanitize_player_name(raw) == expected


# ---- login_required (rule: role check for W2) -------------------------------------------

def test_login_required_blocks_without_session_and_allows_with_it(app):
    bp = Blueprint("probe", __name__)

    @bp.route("/probe")
    @login_required
    def probe():
        return "inside"

    app.register_blueprint(bp)
    client = app.test_client()
    r = client.get("/probe")
    assert r.status_code == 302 and "/login?next=" in r.headers["Location"]
    with client.session_transaction() as sess:
        sess["admin_id"] = 1
    r = client.get("/probe")
    assert r.status_code == 200 and r.get_data(as_text=True) == "inside"


def test_login_required_only_looks_for_the_key_not_a_valid_admin(app):
    """Documents the control: any session with admin_id passes, even for an id that does not exist."""
    bp = Blueprint("probe2", __name__)

    @bp.route("/probe2")
    @login_required
    def probe2():
        return "inside"

    app.register_blueprint(bp)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["admin_id"] = 424242
    assert client.get("/probe2").status_code == 200


# ---- models -----------------------------------------------------------------------------

def test_team_to_dict_has_the_documented_keys_and_values(app):
    t = make_tournament()
    team = make_team(t, "Alpha", confirmed=False, checked_in=True)
    d = team.to_dict()
    assert set(d) == {"id", "name", "player1", "player2", "tournament_id", "is_confirmed",
                      "is_checked_in", "seed", "registered_at"}
    assert d["name"] == "Alpha" and d["is_confirmed"] is False and d["is_checked_in"] is True
    assert d["seed"] is None and d["registered_at"] is not None


def test_team_to_dict_registered_at_none_branch(app):
    from app.models import Team
    assert Team(name="X", player1="a", player2="b").to_dict()["registered_at"] is None


def test_tournament_to_public_dict_hides_the_code_and_counts_teams(app):
    t = make_tournament(max_teams=3, description="d")
    make_team(t, "One")
    make_team(t, "Two", confirmed=False)
    d = t.to_public_dict()
    assert "registration_code" not in d and "owner_id" not in d
    assert d["registered_teams"] == 2 and d["spots_remaining"] == 1 and d["max_teams"] == 3
    assert d["event_date"] is None and d["location"] is None


def test_tournament_to_public_dict_event_date_branch(app):
    from datetime import datetime
    t = make_tournament(event_date=datetime(2026, 12, 1, 9, 0))
    assert t.to_public_dict()["event_date"] == "2026-12-01T09:00:00"
