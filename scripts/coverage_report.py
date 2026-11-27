"""One reproducible coverage run that says what every number measures.

    python scripts/coverage_report.py                 # tests/team, writes HTML, XML and JSON
    python scripts/coverage_report.py --tests tests   # the whole tests tree (upstream tests included)

It runs pytest with coverage over the whole of app/ (the files named by .coveragerc), writes
  docs/evidence/coverage/index.html   HTML report
  coverage.xml                        for SonarCloud
  coverage.json                       for scripts/scoped_coverage.py
and then prints three clearly labelled figures:
  WHOLE APP   every statement and branch of app/*   (the TA's reading of "all server-side business logic")
  SCOPED      only the line ranges in scripts/scoped_coverage.py (the two registered workflows)
  SUITE       how many tests passed, failed, xfailed, errored
Nothing is excluded or omitted here. If the suite is not green or pytest reported collection errors,
the figures are marked UNTRUSTED, because tests that did not run do not count.

"Combined %" is what coverage.py prints as TOTAL: (covered statements + covered branches) divided by
(statements + branches). The statement-only and branch-only percentages are printed beside it.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pct(part, whole):
    return 100.0 if whole == 0 else 100.0 * part / whole


def summarise(coverage_json):
    """Totals and per-file rows from a coverage.py JSON report."""
    data = json.loads(Path(coverage_json).read_text(encoding="utf-8"))
    rows = []
    for name, f in sorted(data["files"].items()):
        s = f["summary"]
        rows.append({"file": name.replace("\\", "/"), "statements": s["num_statements"],
                     "missing": s["missing_lines"], "branches": s["num_branches"],
                     "missing_branches": s["missing_branches"], "partial": s.get("num_partial_branches", 0),
                     "combined": s["percent_covered"]})
    t = data["totals"]
    total = {"statements": t["num_statements"], "missing": t["missing_lines"], "branches": t["num_branches"],
             "missing_branches": t["missing_branches"], "partial": t.get("num_partial_branches", 0),
             "combined": t["percent_covered"],
             "statement_pct": pct(t["num_statements"] - t["missing_lines"], t["num_statements"]),
             "branch_pct": pct(t["num_branches"] - t["missing_branches"], t["num_branches"])}
    return rows, total


def parse_pytest_summary(text):
    """Counts from pytest's last summary line, e.g. '3 failed, 471 passed, 40 xfailed in 115s'."""
    counts = {k: 0 for k in ("passed", "failed", "xfailed", "xpassed", "skipped", "error", "errors")}
    for line in reversed(text.strip().splitlines()):
        if re.search(r"\bin \d+(\.\d+)?s\b", line):
            for number, word in re.findall(r"(\d+) (passed|failed|xfailed|xpassed|skipped|errors?)", line):
                counts[word] += int(number)
            break
    counts["error"] += counts.pop("errors")
    return counts



ALLOWED_TEST_TARGETS = {
    "tests/team",
    "tests/team/test_can_register.py",
    "tests/team/test_register_routes.py",
    "tests/team/test_admin_registration.py",
    "tests/team/test_api_register.py",
    "tests/team/test_api_register_strict.py",
    "tests/team/test_api_generated.py",
}

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--html", default="docs/evidence/coverage")
    args = ap.parse_args(argv)

    html_path = Path(args.html).resolve()
    evidence_path = (ROOT / "docs" / "evidence").resolve()

    if html_path != evidence_path and evidence_path not in html_path.parents:
        ap.error("--html must be inside docs/evidence")
        
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/team",
        "--cov",
        "--cov-branch",
        "--cov-report=term",
        f"--cov-report=html:{html_path}",
        "--cov-report=xml:coverage.xml",
        "--cov-report=json:coverage.json",
        "-q",
        "-p",
        "no:cacheprovider"
    ]

    print("running:", " ".join(cmd), "\n")

    run = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    out = run.stdout + run.stderr
    counts = parse_pytest_summary(out)
    interrupted = "Interrupted" in out or "error" in out.lower().split("short test summary info")[-1][:4000]
    trusted = run.returncode == 0 and counts["failed"] == 0 and counts["error"] == 0 and not interrupted

    if not (ROOT / "coverage.json").exists():
        print(out[-3000:])
        print("No coverage.json was written: pytest did not get as far as running tests.")
        return 2
    rows, total = summarise(ROOT / "coverage.json")

    print(f"{'file':34s} {'stmts':>6s} {'miss':>5s} {'branch':>7s} {'miss':>5s} {'part':>5s} {'combined':>9s}")
    for r in rows:
        print(f"{r['file']:34s} {r['statements']:6d} {r['missing']:5d} {r['branches']:7d} "
              f"{r['missing_branches']:5d} {r['partial']:5d} {r['combined']:8.1f}%")
    print(f"\nWHOLE APP (all of app/*): {total['statements']} statements, {total['missing']} missed; "
          f"{total['branches']} branches, {total['missing_branches']} missed, {total['partial']} partial")
    print(f"  statements {total['statement_pct']:.1f} %   branches {total['branch_pct']:.1f} %   "
          f"combined (coverage.py TOTAL) {total['combined']:.1f} %")
    print("\nSCOPED (only the registered workflows, from scripts/scoped_coverage.py):")
    scoped = subprocess.run([sys.executable, "scripts/scoped_coverage.py"], cwd=ROOT, capture_output=True, text=True)
    for line in scoped.stdout.splitlines():
        if line.startswith(("In-scope", "file ", "app/")):
            print("  " + line)
    print(f"\nSUITE ({' '.join(args.tests)}): " + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
    if not trusted:
        print("\nUNTRUSTED: the suite is not green or pytest reported errors. Tests that did not run do not "
              "count, so these figures are lower than the suite would reach. Last lines of the output:\n")
        print("\n".join(out.strip().splitlines()[-25:]))
        return 1
    print(f"\nHTML report: {args.html}/index.html   XML: coverage.xml (SonarCloud)   JSON: coverage.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
