"""Small AST mutation tester with custom operators for the registration business rules.

Why this exists: mutmut 3 has no plug-in point for custom operators, and the brief asks for at
least two operators built from our own rules. This script holds both kinds:

  standard   cmp_boundary   >= <-> >, < <-> <=, == <-> !=
             bool_swap      and <-> or
             not_removal    `not x` -> `x`
             int_shift      integer constant +1 / -1
             str_mutation   text constant gets "XX" appended (shows weak message assertions)
  custom     limit_shift          rule 1: len(...) compared with a limit, limit +1 / -1
             confirmation_flip    rule 3: is_confirmed=<expr> gets its `not` toggled
             capacity_ignore_pending  rule 1/A4: get_registered_team_count() -> get_confirmed_team_count()
             check_order_swap     rule 2: two neighbouring guard clauses (if ...: return) swap places

Each mutant is written into a throw-away copy of the project, the team tests run against it, and
the mutant is KILLED if pytest fails (or times out) and SURVIVED if it passes.

    python scripts/mutate_rules.py --list                       # count mutants, run nothing
    python scripts/mutate_rules.py --min-score 80               # run all, exit 1 below 80 %
    python scripts/mutate_rules.py --only app/models.py:173-191 --out mutation.json
    python scripts/mutate_rules.py --limit 40 --seed 1          # random sample

Mutated source is re-printed with ast.unparse; the project files themselves are never touched.
"""
import argparse
import ast
import copy
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# file -> (first line, last line): the business-rule code (same ranges as scoped_coverage.py)
DEFAULT_TARGETS = {
    "app/models.py": (173, 191),
    "app/blueprints/register.py": (1, 130),
    "app/blueprints/api.py": (579, 658),
}
# Tests that exercise the business-rule code. Running all of tests/team for every mutant became
# too slow once the whole-app tests were added (about 6 minutes per run), so mutants are tried
# against these files only. Pass --tests tests/team to use everything.
DEFAULT_TESTS = [
    "tests/team/test_can_register.py", "tests/team/test_register_routes.py",
    "tests/team/test_admin_registration.py", "tests/team/test_api_register.py",
    "tests/team/test_api_register_strict.py", "tests/team/test_api_generated.py",
]
COPY = ["app", "tests", "scripts", "docs/api", "config.py", "run.py", ".coveragerc"]

CMP_SWAP = {ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}


def _call_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        return f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
    return None


def _is_guard(stmt):
    return (isinstance(stmt, ast.If) and not stmt.orelse and len(stmt.body) == 1
            and isinstance(stmt.body[0], ast.Return))


def sites(tree, lo, hi):
    """Yield (operator, kind, walk index, variant, line, description) for one module."""
    nodes = list(ast.walk(tree))
    docstrings = set()
    for n in nodes:
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            docstrings.add(id(n.body[0].value))
    for i, n in enumerate(nodes):
        line = getattr(n, "lineno", None)
        if line is None or not (lo <= line <= hi):
            continue
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            op = type(n.ops[0])
            if op in CMP_SWAP:
                yield "cmp_boundary", "standard", i, 0, line, f"{op.__name__} -> {CMP_SWAP[op].__name__}"
            left, right = n.left, n.comparators[0]
            if _call_name(left) == "len" and isinstance(right, ast.Constant) and isinstance(right.value, int):
                for v in (1, 2):
                    yield "limit_shift", "custom", i, v, line, f"len limit {right.value} -> {right.value + (1 if v == 1 else -1)}"
        if isinstance(n, ast.BoolOp):
            yield "bool_swap", "standard", i, 0, line, "And <-> Or"
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            yield "not_removal", "standard", i, 0, line, "remove not"
        if isinstance(n, ast.Constant) and type(n.value) is int and id(n) not in docstrings:
            for v in (1, 2):
                yield "int_shift", "standard", i, v, line, f"{n.value} -> {n.value + (1 if v == 1 else -1)}"
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 3 and id(n) not in docstrings:
            yield "str_mutation", "standard", i, 0, line, f"text {n.value[:25]!r} + XX"
        if isinstance(n, ast.keyword) and n.arg == "is_confirmed":
            yield "confirmation_flip", "custom", i, 0, line, "toggle `not` on is_confirmed"
        if _call_name(n) == "get_registered_team_count":
            yield "capacity_ignore_pending", "custom", i, 0, line, "registered count -> confirmed count"
        if isinstance(n, (ast.FunctionDef, ast.Module)):
            body = n.body
            for k in range(len(body) - 1):
                if _is_guard(body[k]) and _is_guard(body[k + 1]) and lo <= body[k].lineno <= hi:
                    yield "check_order_swap", "custom", i, k, body[k].lineno, f"swap guards at lines {body[k].lineno} and {body[k + 1].lineno}"


def apply(tree, op, index, variant):
    """Return a mutated deep copy of tree (the walk index identifies the node)."""
    t = copy.deepcopy(tree)
    nodes = list(ast.walk(t))
    n = nodes[index]
    if op == "cmp_boundary":
        n.ops[0] = CMP_SWAP[type(n.ops[0])]()
    elif op == "limit_shift":
        c = n.comparators[0]
        c.value += 1 if variant == 1 else -1
    elif op == "bool_swap":
        n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
    elif op == "not_removal":
        parent = next(p for p in nodes for f in ast.iter_child_nodes(p) if f is n)
        for field, value in ast.iter_fields(parent):
            if value is n:
                setattr(parent, field, n.operand)
            elif isinstance(value, list):
                parent_list = value
                for j, item in enumerate(parent_list):
                    if item is n:
                        parent_list[j] = n.operand
    elif op == "int_shift":
        n.value += 1 if variant == 1 else -1
    elif op == "str_mutation":
        n.value = n.value + "XX"
    elif op == "confirmation_flip":
        v = n.value
        n.value = v.operand if isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.Not) else ast.UnaryOp(ast.Not(), v)
    elif op == "capacity_ignore_pending":
        n.func.attr = "get_confirmed_team_count"
    elif op == "check_order_swap":
        n.body[variant], n.body[variant + 1] = n.body[variant + 1], n.body[variant]
    ast.fix_missing_locations(t)
    return t


def enumerate_mutants(targets):
    out = []
    for rel, (lo, hi) in targets.items():
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for op, kind, idx, variant, line, desc in sites(tree, lo, hi):
            out.append({"file": rel, "operator": op, "kind": kind, "index": idx, "variant": variant,
                        "line": line, "description": desc})
    for number, m in enumerate(out, 1):
        m["id"] = number
    return out


def run_pytest(workdir, timeout, tests):
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", *tests, "-x", "-q", "-p", "no:cacheprovider",
                            "--no-header"], cwd=workdir, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout[-400:]
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", help="file[:first-last], repeatable; default is the rule code")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--tests", nargs="+", default=DEFAULT_TESTS, help="test files or folders to run per mutant")
    ap.add_argument("--min-score", type=float, default=0.0)
    ap.add_argument("--out", default="mutation-report.json")
    args = ap.parse_args(argv)

    targets = DEFAULT_TARGETS
    if args.only:
        targets = {}
        for spec in args.only:
            f, _, r = spec.partition(":")
            lo, hi = (int(x) for x in r.split("-")) if r else (1, 10**6)
            targets[f] = (lo, hi)
    mutants = enumerate_mutants(targets)
    if args.limit and args.limit < len(mutants):
        mutants = sorted(random.Random(args.seed).sample(mutants, args.limit), key=lambda m: m["id"])
    by_op = {}
    for m in mutants:
        by_op[m["operator"]] = by_op.get(m["operator"], 0) + 1
    print(f"{len(mutants)} mutants: " + ", ".join(f"{k}={v}" for k, v in sorted(by_op.items())))
    if args.list:
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="mutants-"))
    try:
        for item in COPY:
            src = ROOT / item
            if src.exists():
                dst = tmp / item
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")) if src.is_dir() else shutil.copy2(src, dst)
        code, tail = run_pytest(tmp, args.timeout * 3, args.tests)
        if code != 0:
            print("The unmutated tests do not pass, so mutation results would be meaningless:\n" + tail)
            return 2
        cache = {}
        results = []
        for m in mutants:
            path = tmp / m["file"]
            if m["file"] not in cache:
                cache[m["file"]] = (ROOT / m["file"]).read_text(encoding="utf-8")
            tree = ast.parse(cache[m["file"]])
            path.write_text(ast.unparse(apply(tree, m["operator"], m["index"], m["variant"])) + "\n", encoding="utf-8")
            code, tail = run_pytest(tmp, args.timeout, args.tests)
            m["status"] = "survived" if code == 0 else "killed"
            results.append(m)
            path.write_text(cache[m["file"]], encoding="utf-8")
            print(f"[{m['id']:3d}] {m['status']:8s} {m['operator']:24s} {m['file']}:{m['line']} {m['description']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    killed = sum(1 for m in results if m["status"] == "killed")
    score = 100 * killed / len(results) if results else 100.0
    summary = {"total": len(results), "killed": killed, "survived": len(results) - killed, "score": round(score, 1),
               "per_operator": {}, "survivors": [m for m in results if m["status"] == "survived"]}
    for m in results:
        d = summary["per_operator"].setdefault(m["operator"], {"kind": m["kind"], "total": 0, "killed": 0})
        d["total"] += 1
        d["killed"] += m["status"] == "killed"
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nmutation score {score:.1f}% ({killed}/{len(results)} killed); report in {args.out}")
    if score < args.min_score:
        print(f"FAIL: below the threshold of {args.min_score}%")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
