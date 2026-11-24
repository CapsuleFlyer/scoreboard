"""Tests for the custom mutation operators in scripts/mutate_rules.py (no Flask, no database)."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mutate_rules as mr  # noqa: E402

SAMPLE = '''
def can_register(self):
    """doc"""
    if not self.open:
        return False, "closed"
    if self.status != "registration":
        return False, "started"
    if self.get_registered_team_count() >= self.max_teams:
        return False, "full"
    return True, "OK"

def make(name, t):
    if len(name) > 20:
        return None
    return Team(name=name, is_confirmed=not t.require_confirmation)
'''


def mutants():
    tree = ast.parse(SAMPLE)
    return tree, [s for s in mr.sites(tree, 1, 100)]


def apply_to_source(op, pick=0):
    tree, found = mutants()
    chosen = [s for s in found if s[0] == op][pick]
    return ast.unparse(mr.apply(tree, chosen[0], chosen[2], chosen[3]))


def test_every_mutant_compiles_and_differs_from_the_original():
    tree, found = mutants()
    original = ast.unparse(tree)
    assert found
    for op, kind, idx, variant, line, desc in found:
        text = ast.unparse(mr.apply(tree, op, idx, variant))
        compile(text, "<mutant>", "exec")
        assert text != original, (op, desc)


def test_docstring_is_not_mutated():
    _, found = mutants()
    assert not any(s[0] == "str_mutation" and "doc" in s[5] for s in found)


def test_limit_shift_moves_the_length_limit():
    assert "len(name) > 21" in apply_to_source("limit_shift", 0)
    assert "len(name) > 19" in apply_to_source("limit_shift", 1)


def test_confirmation_flip_removes_the_not():
    out = apply_to_source("confirmation_flip")
    assert "is_confirmed=t.require_confirmation" in out


def test_capacity_ignore_pending_swaps_the_count_method():
    out = apply_to_source("capacity_ignore_pending")
    assert "get_confirmed_team_count()" in out and "get_registered_team_count" not in out


def test_check_order_swap_exchanges_neighbouring_guards():
    out = apply_to_source("check_order_swap", 0)
    assert out.index("self.status") < out.index("self.open")


def test_cmp_boundary_turns_gte_into_gt():
    outs = [apply_to_source("cmp_boundary", i) for i in range(3)]
    assert any("get_registered_team_count() > self.max_teams" in o for o in outs)


def test_not_removal():
    out = apply_to_source("not_removal", 0)
    assert "if self.open:" in out


def test_two_custom_operator_kinds_are_reported_as_custom():
    _, found = mutants()
    custom = {s[0] for s in found if s[1] == "custom"}
    assert {"limit_shift", "confirmation_flip", "capacity_ignore_pending", "check_order_swap"} <= custom
