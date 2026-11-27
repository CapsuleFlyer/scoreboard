"""Run the k6 load tests: one user twice, five users twice, each on a fresh server and database.

    python scripts/run_perf.py                  # 4 runs of 10 s warm-up + 60 s measured
    python scripts/run_perf.py --measure 60 --p95 500 --max-fail 0.01

Needs k6 on the PATH (https://grafana.com/docs/k6/latest/set-up/install-k6/ ; winget install k6).
Writes to docs/evidence/performance/: environment.txt, k6-<users>u-run<n>.txt (k6 output),
summary-<users>u-run<n>.json (k6 --summary-export) and results.md (the table below). The limits are
passed to k6 and are the ones in docs/performance.md: set them BEFORE you run and commit that file.

p95 is the 95th percentile of http_req_duration in the measured phase only. Requests per second is the
measured request count divided by the measured duration (k6's own rate divides by the whole run).
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "performance"


def pct(summary_metric):
    """Percentage of 'true' samples of a k6 Rate metric, from --summary-export (versions differ)."""
    passes, fails = summary_metric.get("passes"), summary_metric.get("fails")
    if passes is not None and fails is not None and passes + fails > 0:
        return 100.0 * passes / (passes + fails)
    value = summary_metric.get("value", summary_metric.get("rate", 0.0))
    return 100.0 * value


def summarise_run(summary, measure_seconds, p95_limit_ms, max_fail_pct, readback=None):
    """One results row from a k6 summary export."""
    m = summary["metrics"]
    p95 = m["http_req_duration{phase:measure}"]["p(95)"]
    count = m["http_reqs{phase:measure}"]["count"]
    fail = pct(m["unexpected_failures{phase:measure}"])
    registered = int(m.get("registered_ok", {}).get("count", 0))
    row = {"p95_ms": p95, "requests": count, "req_per_s": count / measure_seconds, "failed_pct": fail,
           "registered_ok": registered, "p95_ok": p95 < p95_limit_ms, "fail_ok": fail < max_fail_pct}
    if readback:
        row["readback_delta"] = readback[1] - readback[0]
        row["readback_ok"] = row["readback_delta"] == registered
    return row


def parse_readback(text):
    found = re.search(r"READBACK start=(\d+) end=(\d+)", text)
    return (int(found.group(1)), int(found.group(2))) if found else None


def environment(k6):
    lines = [f"date: {time.strftime('%Y-%m-%d %H:%M:%S')}", f"os: {platform.platform()}",
             f"cpu: {platform.processor()} ({os.cpu_count()} logical cores)", f"python: {sys.version.split()[0]}",
             "server: Werkzeug threaded development server, SQLite file database (fresh for every run)"]
    for name, cmd in (("k6", [k6, "version"]), ("git commit", ["git", "rev-parse", "HEAD"])):
        try:
            lines.append(f"{name}: " + subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.strip())
        except OSError:
            lines.append(f"{name}: unknown")
    return "\n".join(lines) + "\n"


def wait_for(url, seconds=30):
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--users", nargs="+", type=int, default=[1, 5])
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--measure", type=int, default=60)
    ap.add_argument("--p95", type=int, default=500, help="limit in ms")
    ap.add_argument("--max-fail", type=float, default=0.01, help="limit as a fraction, 0.01 = 1 %%")
    ap.add_argument("--port", type=int, default=5056)
    args = ap.parse_args(argv)

    k6 = shutil.which("k6")
    if not k6:
        print("k6 not found. Install it (winget install k6) and open a new terminal.")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "environment.txt").write_text(environment(k6), encoding="utf-8")
    base = f"http://127.0.0.1:{args.port}"
    rows = []
    for users in args.users:
        for run in range(1, args.runs + 1):
            server = subprocess.Popen([sys.executable, "scripts/perf_server.py", "--port", str(args.port)],
                                      cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                if not wait_for(base + "/register/"):
                    print("server did not start")
                    return 2
                summary_file = OUT / f"summary-{users}u-run{run}.json"
                cmd = [k6, "run", "-e", f"VUS={users}", "-e", f"BASE_URL={base}", "-e", f"P95_MS={args.p95}",
                       "-e", f"MAX_FAIL={args.max_fail}", "-e", f"WARMUP={args.warmup}s",
                       "-e", f"MEASURE={args.measure}s", f"--summary-export={summary_file}", "scripts/perf_register.js"]
                print("running:", " ".join(cmd), flush=True)
                result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)   # exit 99 = a threshold failed
                text = result.stdout + result.stderr
                (OUT / f"k6-{users}u-run{run}.txt").write_text(text, encoding="utf-8")
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                row = summarise_run(summary, args.measure, args.p95, args.max_fail * 100, parse_readback(text))
                rows.append((users, run, row))
                print(f"  p95 {row['p95_ms']:.0f} ms, {row['req_per_s']:.1f} req/s, {row['failed_pct']:.2f} % failed")
            finally:
                server.terminate()
                server.wait(timeout=20)
    lines = [f"Limits: p95 < {args.p95} ms, unexpected failures < {args.max_fail * 100:g} %. "
             f"Measured phase {args.measure} s after a {args.warmup} s warm-up.\n",
             "| Users | Run | p95 (ms) | Requests/s | Failed (%) | Registered | Read-back matches | Within limits |",
             "|---|---|---|---|---|---|---|---|"]
    for users, run, r in rows:
        rb = {True: "yes", False: "NO", None: "n/a"}[r.get("readback_ok")]
        lines.append(f"| {users} | {run} | {r['p95_ms']:.0f} | {r['req_per_s']:.1f} | {r['failed_pct']:.2f} | "
                     f"{r['registered_ok']} | {rb} | {'yes' if r['p95_ok'] and r['fail_ok'] and r.get('readback_ok') is True else 'NO'} |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
