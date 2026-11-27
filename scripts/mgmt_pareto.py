"""Pareto analysis of defects by category, from docs/management/defects.csv.

    python scripts/mgmt_pareto.py          # prints the table, writes docs/management/pareto.svg and pareto.md

The CSV is the single list of defects (id, title, severity, priority, category, status). Keep it equal to
the GitHub issues: it is a snapshot, not a second source of truth. Standard library only.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFECTS = ROOT / "docs" / "management" / "defects.csv"


def read_defects(path=DEFECTS):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pareto(defects):
    counts = Counter(d["category"] for d in defects)
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    total, running, rows = sum(counts.values()), 0, []
    for category, count in ordered:
        running += count
        rows.append({"category": category, "count": count, "pct": round(100 * count / total, 1),
                     "cumulative_pct": round(100 * running / total, 1)})
    return rows


def svg(rows, width=640, height=320):
    left, bottom, top = 50, 70, 20
    plot_w, plot_h = width - left - 50, height - bottom - top
    peak = max(r["count"] for r in rows)
    bar_w = plot_w / len(rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Pareto chart of defects by category" font-family="sans-serif" font-size="11">',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333"/>',
             f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333"/>']
    points = []
    for i, r in enumerate(rows):
        h = plot_h * r["count"] / peak
        x = left + i * bar_w
        parts.append(f'<rect x="{x + 6:.1f}" y="{top + plot_h - h:.1f}" width="{bar_w - 12:.1f}" height="{h:.1f}" fill="#4a7ebb"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h - h - 4:.1f}" text-anchor="middle">{r["count"]}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h + 14}" text-anchor="end" '
                     f'transform="rotate(-35 {x + bar_w / 2:.1f} {top + plot_h + 14})">{r["category"]}</text>')
        points.append(f'{x + bar_w / 2:.1f},{top + plot_h - plot_h * r["cumulative_pct"] / 100:.1f}')
    parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#c0392b" stroke-width="2"/>')
    parts.append(f'<text x="{left + plot_w + 6}" y="{top + 4}" fill="#c0392b">100%</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def main():
    rows = pareto(read_defects())
    lines = ["| Category | Defects | % | Cumulative % |", "|---|---|---|---|"]
    lines += [f"| {r['category']} | {r['count']} | {r['pct']} | {r['cumulative_pct']} |" for r in rows]
    out = ROOT / "docs" / "management"
    (out / "pareto.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "pareto.svg").write_text(svg(rows), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
