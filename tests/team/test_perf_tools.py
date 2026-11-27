"""Tests for the pure parts of the performance, Pareto and estimation scripts (no Flask, no k6)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mgmt_pareto  # noqa: E402
import pert  # noqa: E402
import run_perf  # noqa: E402


def k6_summary(p95=120.0, requests=6000, passes=3, fails=5997, registered=6010):
    return {"metrics": {
        "http_req_duration{phase:measure}": {"avg": 50.0, "p(95)": p95},
        "http_reqs{phase:measure}": {"count": requests, "rate": requests / 70},
        "unexpected_failures{phase:measure}": {"passes": passes, "fails": fails, "value": passes / (passes + fails)},
        "registered_ok": {"count": registered, "rate": 1.0}}}


def test_summarise_run_uses_the_measured_window_for_throughput():
    row = run_perf.summarise_run(k6_summary(), 60, 500, 1.0, readback=(0, 6010))
    assert row["req_per_s"] == 100.0                 # 6000 / 60 s, not k6's whole-run rate
    assert row["p95_ok"] and row["fail_ok"] and row["readback_ok"] and row["readback_delta"] == 6010


def test_summarise_run_flags_a_breach_and_a_readback_mismatch():
    row = run_perf.summarise_run(k6_summary(p95=800.0, passes=100, fails=5900), 60, 500, 1.0, readback=(0, 6000))
    assert not row["p95_ok"] and not row["fail_ok"] and row["readback_ok"] is False


def test_rate_percentage_falls_back_to_value_or_rate_keys():
    assert run_perf.pct({"value": 0.02}) == 2.0 and run_perf.pct({"rate": 0.5}) == 50.0
    assert run_perf.pct({"passes": 1, "fails": 3}) == 25.0


def test_parse_readback():
    assert run_perf.parse_readback("x READBACK start=4 end=9 y") == (4, 9)
    assert run_perf.parse_readback("nothing") is None


def test_pareto_orders_categories_and_accumulates(tmp_path):
    csv_file = tmp_path / "d.csv"
    csv_file.write_text("id,title,severity,priority,category,status\n"
                        "DR-1,a,major,P2,validation,open\nDR-2,b,minor,P3,validation,open\n"
                        "DR-3,c,minor,P3,state-rules,open\nDR-4,d,minor,P3,dependency,open\n", encoding="utf-8")
    rows = mgmt_pareto.pareto(mgmt_pareto.read_defects(csv_file))
    assert [(r["category"], r["count"]) for r in rows] == [("validation", 2), ("dependency", 1), ("state-rules", 1)]
    assert [r["cumulative_pct"] for r in rows] == [50.0, 75.0, 100.0]
    assert "<svg" in mgmt_pareto.svg(rows)


def test_pert_three_point_estimate_and_variance(tmp_path):
    csv_file = tmp_path / "e.csv"
    csv_file.write_text("area,optimistic_h,most_likely_h,pessimistic_h,actual_h\n"
                        "Unit tests,4,6,14,9\nCI,2,3,4,\n", encoding="utf-8")
    rows = pert.estimate(pert.read_rows(csv_file))
    assert rows[0]["expected"] == 7.0 and rows[0]["sd"] == round((14 - 4) / 6, 2)
    assert rows[0]["variance"] == 2.0 and rows[1]["variance"] is None       # no actual yet
