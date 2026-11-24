"""Cyclomatic complexity per function (stdlib only), to CHECK your hand calculation.

Do the control flow graph and V(G) = E - N + 2 by hand first; this script is the cross-check
you compare with SonarQube. Counting rule (same idea as Sonar): 1 + number of if/elif, for,
while, except, ternary, comprehension-if, plus one per extra operand of and/or.
SonarQube reports per file, so compare the sum of the functions of one file with its figure.

    python scripts/cyclomatic.py app/blueprints/register.py
    python scripts/cyclomatic.py app/models.py --function can_register
"""
import ast
import sys


def complexity(fn):
    score = 1
    for n in ast.walk(fn):
        if n is not fn and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(n, (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler, ast.AsyncFor)):
            score += 1
        elif isinstance(n, ast.comprehension):
            score += len(n.ifs)
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
    return score


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    only = argv[argv.index("--function") + 1] if "--function" in argv else None
    tree = ast.parse(open(path, encoding="utf-8").read())
    total = 0
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and (only is None or n.name == only):
            c = complexity(n)
            total += c
            print(f"{n.name:35s} lines {n.lineno}-{n.end_lineno}  V(G) = {c}")
    print(f"{'sum of functions':35s} {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
