"""Tests for scripts/coverage_report.py (pure: no Flask, no pytest-cov needed)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import coverage_report as cr  # noqa: E402


def write_report(path):
    def f(stmts, miss, br, mbr, part, pc):
        return {"summary": {"num_statements": stmts, "missing_lines": miss, "num_branches": br,
                            "missing_branches": mbr, "num_partial_branches": part, "percent_covered": pc}}
    data = {"files": {"app\\a.py": f(10, 0, 4, 0, 0, 100.0), "app\\b.py": f(10, 5, 4, 2, 1, 55.0)},
            "totals": {"num_statements": 20, "missing_lines": 5, "num_branches": 8, "missing_branches": 2,
                       "num_partial_branches": 1, "percent_covered": 75.0}}
    path.write_text(json.dumps(data), encoding="utf-8")


def test_summarise_reads_files_and_totals(tmp_path):
    report = tmp_path / "coverage.json"
    write_report(report)
    rows, total = cr.summarise(report)
    assert [r["file"] for r in rows] == ["app/a.py", "app/b.py"]          # Windows separators normalised
    assert rows[1]["missing"] == 5 and rows[1]["partial"] == 1
    assert total["statement_pct"] == 75.0 and total["branch_pct"] == 75.0 and total["combined"] == 75.0


def test_percentages_handle_empty_denominators():
    assert cr.pct(0, 0) == 100.0 and cr.pct(1, 4) == 25.0


def test_parse_pytest_summary_counts_every_outcome():
    text = "....\n=== 3 failed, 471 passed, 40 xfailed, 1 error, 13 warnings in 115.05s (0:01:55) ==="
    counts = cr.parse_pytest_summary(text)
    assert (counts["failed"], counts["passed"], counts["xfailed"], counts["error"]) == (3, 471, 40, 1)


def test_parse_pytest_summary_without_a_summary_line():
    assert sum(cr.parse_pytest_summary("nothing useful here").values()) == 0
