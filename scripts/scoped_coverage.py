"""Report statement and branch coverage for the in-scope business logic only.

coverage.py reports per file, but our scope is specific functions inside larger files
(docs/test-basis.md section 3). This script reads coverage.json and counts only the
line ranges listed in SCOPE below.

Gate use (CI): --min-statements 90 --min-branches 85 exits 1 only when a percentage is below
its minimum. Without --min-* flags any uncovered line fails (the 100 % target).

Usage (from the repo root):
    python -m pytest tests/team --cov --cov-report=json
    python scripts/scoped_coverage.py            # prints the table, exit code 1 if below 100%
    python scripts/scoped_coverage.py --list     # also lists every uncovered line and branch

If code moves, update SCOPE. The line ranges are function boundaries, taken from the source.
"""
import json
import sys
from pathlib import Path

REPORT = Path("coverage.json")

# file -> list of (first line, last line, label)
SCOPE = {
    "app/blueprints/register.py": [(1, 130, "whole file: public registration routes")],
    "app/blueprints/admin.py": [
        (381, 386, "admin_tournament_registrations"),
        (391, 405, "admin_confirm_team"),
        (410, 447, "admin_add_team_to_tournament"),
        (452, 468, "admin_reject_team"),
        (473, 482, "admin_checkin_team"),
        (487, 501, "admin_toggle_registration"),
    ],
    "app/blueprints/api.py": [
        (579, 595, "api_validate_code"),
        (599, 658, "api_register_team"),
    ],
    "app/models.py": [
        (114, 125, "Team.to_dict"),
        (173, 191, "registered/confirmed counts and can_register"),
        (215, 230, "Tournament.to_public_dict"),
    ],
    "app/utils.py": [
        (38, 55, "sanitize_team_name"),
        (58, 74, "sanitize_player_name"),
    ],
    "app/blueprints/auth.py": [(19, 26, "login_required")],
}


def in_ranges(line, ranges):
    return any(a <= line <= b for a, b, _ in ranges)


def _arg(name):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else None


def main():
    show_list = "--list" in sys.argv
    min_s, min_b = _arg("--min-statements"), _arg("--min-branches")
    if not REPORT.exists():
        print("coverage.json not found. Run: python -m pytest tests/team --cov --cov-report=json")
        return 2
    files = json.loads(REPORT.read_text(encoding="utf-8"))["files"]

    total_s = cov_s = total_b = cov_b = 0
    print(f"{'file':32s} {'stmts':>6s} {'miss':>5s} {'branches':>9s} {'miss':>5s}")
    uncovered = []
    for path, ranges in SCOPE.items():
        key = path if path in files else path.replace("/", "\\")
        data = files[key]
        executed = [l for l in data["executed_lines"] if in_ranges(l, ranges)]
        missing = [l for l in data["missing_lines"] if in_ranges(l, ranges)]
        ex_br = [b for b in data.get("executed_branches", []) if in_ranges(b[0], ranges)]
        mi_br = [b for b in data.get("missing_branches", []) if in_ranges(b[0], ranges)]
        s, ms = len(executed) + len(missing), len(missing)
        b, mb = len(ex_br) + len(mi_br), len(mi_br)
        total_s += s
        cov_s += s - ms
        total_b += b
        cov_b += b - mb
        print(f"{path:32s} {s:6d} {ms:5d} {b:9d} {mb:5d}")
        uncovered += [(path, "line", l) for l in missing] + [(path, "branch", tuple(x)) for x in mi_br]

    pct_s = 100 * cov_s / total_s if total_s else 100
    pct_b = 100 * cov_b / total_b if total_b else 100
    print(f"\nIn-scope statements: {cov_s}/{total_s} = {pct_s:.1f}%")
    print(f"In-scope branches:   {cov_b}/{total_b} = {pct_b:.1f}%")
    if show_list:
        for path, kind, what in uncovered:
            print(f"  uncovered {kind}: {path}:{what}")
    if min_s is not None or min_b is not None:
        ok = pct_s >= (min_s or 0) and pct_b >= (min_b or 0)
        print(f"Gate: statements >= {min_s}%, branches >= {min_b}% -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    return 0 if not uncovered else 1


if __name__ == "__main__":
    sys.exit(main())
