"""Compare two axe-core scans (before / after) and list resolved, remaining and new issues.

    python scripts/a11y_compare.py register-form
reads docs/evidence/accessibility/before/<name>.json and .../after/<name>.json. An issue is the pair
(rule id, target selector). Findings that Lighthouse and axe both report count once: record that
by hand in your report table (element, user impact, proposed fix).
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "accessibility"


def issues(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for v in data["violations"]:
        for node in v["nodes"]:
            out[(v["id"], " ".join(node["target"]) if isinstance(node["target"][0], str) else str(node["target"]))] = \
                (v["impact"], v["help"])
    return out


def main(name):
    before, after = issues(BASE / "before" / f"{name}.json"), issues(BASE / "after" / f"{name}.json")
    resolved = sorted(set(before) - set(after))
    remaining = sorted(set(before) & set(after))
    new = sorted(set(after) - set(before))
    print(f"{name}: before {len(before)} issues, after {len(after)}")
    for title, items, src in (("RESOLVED", resolved, before), ("REMAINING", remaining, after), ("NEW", new, after)):
        print(f"\n{title} ({len(items)})")
        for key in items:
            impact, helptext = src[key]
            print(f"  [{impact}] {key[0]}  {key[1]}  - {helptext}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
