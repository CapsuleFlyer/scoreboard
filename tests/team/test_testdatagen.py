"""Tests for the generator itself (no Flask, no database)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import testdatagen as g  # noqa: E402

SPEC_PATH = ROOT / "docs" / "api" / "openapi.yaml"
GENERATED = ROOT / "tests" / "team" / "generated" / "api_cases.json"


def spec_with(**limits):
    spec = g.load_spec(SPEC_PATH)
    props = spec["paths"]["/api/register/team"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    props["team_name"].update(limits)
    return spec


def lengths(cases, field, valid=None):
    return sorted(len(c["value"]) for c in cases
                  if c["field"] == field and isinstance(c["value"], str)
                  and c["class"].startswith("bva") and (valid is None or c["valid"] == valid))


def test_team_name_bva_is_three_points_around_each_limit():
    cases = g.generate(g.load_spec(SPEC_PATH))
    assert lengths(cases, "team_name") == [0, 1, 2, 19, 20, 21]
    assert lengths(cases, "team_name", valid=False) == [0, 21]
    assert lengths(cases, "player1") == [0, 1, 2, 29, 30, 31]


def test_one_invalid_field_per_case():
    for c in g.generate(g.load_spec(SPEC_PATH)):
        if c["operation"] == "registerTeam" and c["field"] != "code":
            for other in ("code", "team_name", "player1", "player2"):
                if other != c["field"]:
                    assert c["body"][other] == g.load_spec(SPEC_PATH)["paths"]["/api/register/team"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"][other]["example"]


def test_required_missing_and_wrong_types_present():
    cases = g.generate(g.load_spec(SPEC_PATH))
    classes = {(c["field"], c["class"].split("+")[0]) for c in cases if c["operation"] == "registerTeam"}
    assert ("team_name", "missing_required") in classes
    assert ("email", "optional_omitted") in classes
    assert ("team_name", "wrong_type_integer") in classes and ("team_name", "wrong_type_null") in classes
    assert ("team_name", "blank") in classes


def test_changing_a_constraint_changes_the_cases():
    old = g.generate(g.load_spec(SPEC_PATH))
    new = g.generate(spec_with(maxLength=10))
    assert lengths(new, "team_name") == [0, 1, 2, 9, 10, 11]
    lines = g.diff(old, new)
    assert any(l.startswith("+ registerTeam.team_name") and "len=11" in l for l in lines)
    assert any(l.startswith("- registerTeam.team_name") and "len=21" in l for l in lines)
    # 19 and 20 characters were valid values before and are now removed or invalid
    assert any("len=19" in l and l.startswith("-") for l in lines)


def test_raising_the_minimum_moves_the_lower_boundary():
    new = g.generate(spec_with(minLength=3))
    assert lengths(new, "team_name") == [2, 3, 4, 19, 20, 21]
    assert lengths(new, "team_name", valid=False) == [2, 21]


def test_integer_and_enum_rules():
    spec = {"paths": {"/x": {"post": {"operationId": "x", "x-expect": {"valid": {"status": 200}, "invalid": {"status": 400}},
            "requestBody": {"content": {"application/json": {"schema": {
                "required": ["n", "m"], "properties": {
                    "n": {"type": "integer", "minimum": 2, "maximum": 8, "example": 5},
                    "m": {"type": "string", "enum": ["a", "b"], "example": "a"}}}}}}}}}}
    cases = g.generate(spec)
    n = {c["value"]: c["valid"] for c in cases if c["field"] == "n" and isinstance(c["value"], int)}
    assert n == {1: False, 2: True, 3: True, 5: True, 7: True, 8: True, 9: False}
    m = {c["value"]: c["valid"] for c in cases if c["field"] == "m" and isinstance(c["value"], str)}
    assert m == {"a": True, "b": True, "not-in-enum": False}


def test_committed_generated_file_matches_the_spec():
    """Fails when someone edits the spec but forgets to regenerate (the viva live task)."""
    fresh = json.loads(json.dumps(g.generate(g.load_spec(SPEC_PATH)), sort_keys=True))
    assert fresh == json.loads(GENERATED.read_text(encoding="utf-8"))
