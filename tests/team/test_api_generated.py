"""API tests driven by the generator (scripts/testdatagen.py) from docs/api/openapi.yaml.

Every case (EP class or 3-point BVA value, one invalid field at a time) is sent to the real
endpoint and the status, JSON subset and database postcondition are asserted. If the spec
changes, the cases change with it and no test code needs editing.

Wrong-type values (integer, null) currently crash the endpoints with 500 (DR-13, unconfirmed):
those cases are strict xfail, so a fix shows up as XPASS.
Status: written against the source (READ), generator output RUN. Run before citing results.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import testdatagen  # noqa: E402

from app.models import Team  # noqa: E402
from team_support import make_tournament  # noqa: E402

SPEC = ROOT / "docs" / "api" / "openapi.yaml"
CASES = testdatagen.generate(testdatagen.load_spec(SPEC))


def _param(case):
    marks = []
    if case["class"].split("+")[0].startswith("wrong_type"):
        marks.append(pytest.mark.xfail(strict=True, reason="DR-13: non-string JSON value crashes .strip() (500)"))
    return pytest.param(case, id=testdatagen.case_id(case), marks=marks)


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_generated_case(app, client, case):
    app.config["PROPAGATE_EXCEPTIONS"] = False   # a crash must show as 500, not as an exception
    t = make_tournament()
    r = client.post(case["path"], json=case["body"])
    expect = case["expect"]
    assert r.status_code == expect["status"], f"{case['field']}={case['value']!r}"
    data = r.get_json()
    for key, want in expect["json"].items():
        assert data[key] == want
    if case["path"].endswith("/team"):
        stored = Team.query.filter_by(tournament_id=t.id).count()
        assert stored == (1 if case["valid"] else 0)   # invalid input must not create a row
    else:
        assert Team.query.count() == 0                  # validate-code never writes
