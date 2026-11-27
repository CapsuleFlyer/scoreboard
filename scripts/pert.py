"""Three-point (PERT) estimates per area, compared with actual effort.

    python scripts/pert.py            # reads docs/management/estimates.csv, prints and writes estimates.md

Expected = (optimistic + 4 x most likely + pessimistic) / 6. Standard deviation = (pessimistic - optimistic) / 6.
Fill the three estimates BEFORE the work and the actual hours AFTER it; leave actual_h empty until then.
The numbers are yours: nothing is pre-filled.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "docs" / "management" / "estimates.csv"


def read_rows(path=CSV):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(value):
    return None if value is None or str(value).strip() == "" else float(value)


def estimate(rows):
    out = []
    for r in rows:
        o, m, p, a = (num(r.get(k)) for k in ("optimistic_h", "most_likely_h", "pessimistic_h", "actual_h"))
        if None in (o, m, p):
            out.append({"area": r["area"], "expected": None, "sd": None, "actual": a, "variance": None})
            continue
        expected = round((o + 4 * m + p) / 6, 2)
        out.append({"area": r["area"], "expected": expected, "sd": round((p - o) / 6, 2), "actual": a,
                    "variance": None if a is None else round(a - expected, 2)})
    return out


def main():
    rows = estimate(read_rows())
    fmt = lambda v: "" if v is None else f"{v:g}"
    lines = ["| Area | Expected (h) | SD (h) | Actual (h) | Actual - expected (h) |", "|---|---|---|---|---|"]
    lines += [f"| {r['area']} | {fmt(r['expected'])} | {fmt(r['sd'])} | {fmt(r['actual'])} | {fmt(r['variance'])} |" for r in rows]
    known = [r for r in rows if r["expected"] is not None]
    if known:
        lines.append(f"| **Total** | {sum(r['expected'] for r in known):g} | | "
                     f"{sum(r['actual'] or 0 for r in known):g} | |")
    (CSV.parent / "estimates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
