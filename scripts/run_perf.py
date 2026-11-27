
"""Run the k6 load tests: one user twice, five users twice, each on a fresh server and database.

    python scripts/run_perf.py
    python scripts/run_perf.py --measure 60 --p95 500 --max-fail 0.01
"""
import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "performance"


def pct(summary_metric):
    """Percentage of true samples of a k6 Rate metric."""
    passes = summary_metric.get("passes")
    fails = summary_metric.get("fails")

    if passes is not None and fails is not None and passes + fails > 0:
        return 100.0 * passes / (passes + fails)

    value = summary_metric.get("value", summary_metric.get("rate", 0.0))
    return 100.0 * value


def summarise_run(summary, measure_seconds, p95_limit_ms, max_fail_pct, readback=None):
    """One results row from a k6 summary export."""
    metrics = summary["metrics"]
    p95 = metrics["http_req_duration{phase:measure}"]["p(95)"]
    count = metrics["http_reqs{phase:measure}"]["count"]
    fail = pct(metrics["unexpected_failures{phase:measure}"])
    registered = int(metrics.get("registered_ok", {}).get("count", 0))

    row = {
        "p95_ms": p95,
        "requests": count,
        "req_per_s": count / measure_seconds,
        "failed_pct": fail,
        "registered_ok": registered,
        "p95_ok": p95 < p95_limit_ms,
        "fail_ok": fail < max_fail_pct,
    }

    if readback:
        row["readback_delta"] = readback[1] - readback[0]
        row["readback_ok"] = row["readback_delta"] == registered

    return row


def parse_readback(output):
    found = re.search(r"READBACK start=(\d+) end=(\d+)", output)

    if found:
        return int(found.group(1)), int(found.group(2))

    return None


def environment(k6):
    lines = [
        f"date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"os: {platform.platform()}",
        f"cpu: {platform.processor()} ({os.cpu_count()} logical cores)",
        f"python: {sys.version.split()[0]}",
        "server: Werkzeug threaded development server, SQLite file database (fresh for every run)",
    ]

    commands = [
        ("k6", [k6, "version"]),
        ("git commit", ["git", "rev-parse", "HEAD"]),
    ]

    for name, command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )
            lines.append(f"{name}: {result.stdout.strip()}")
        except OSError:
            lines.append(f"{name}: unknown")

    return "\n".join(lines) + "\n"


def wait_for(port, seconds=30):
    """Wait for the local performance server on a fixed loopback address."""
    end = time.monotonic() + seconds

    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)

    return False


def validate_arguments(parser, args):
    """Reject unsafe or unreasonable command-line values."""
    if not 1 <= args.runs <= 10:
        parser.error("--runs must be between 1 and 10")

    if not args.users or any(users < 1 or users > 100 for users in args.users):
        parser.error("--users values must be between 1 and 100")

    if not 1 <= args.warmup <= 300:
        parser.error("--warmup must be between 1 and 300 seconds")

    if not 1 <= args.measure <= 3600:
        parser.error("--measure must be between 1 and 3600 seconds")

    if not 1 <= args.p95 <= 60000:
        parser.error("--p95 must be between 1 and 60000 milliseconds")

    if not 0 < args.max_fail <= 1:
        parser.error("--max-fail must be greater than 0 and at most 1")

    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--users", nargs="+", type=int, default=[1, 5])
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--measure", type=int, default=60)
    parser.add_argument("--p95", type=int, default=500, help="limit in ms")
    parser.add_argument("--max-fail", type=float, default=0.01, help="limit as a fraction")
    parser.add_argument("--port", type=int, default=5056)

    args = parser.parse_args(argv)
    validate_arguments(parser, args)

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
            server_command = [
                sys.executable,
                "scripts/perf_server.py",
                "--port",
                str(args.port),
            ]

            server = subprocess.Popen(
                server_command,
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )

            try:
                if not wait_for(args.port):
                    print("server did not start")
                    return 2

                summary_file = OUT / f"summary-{users}u-run{run}.json"

                k6_command = [
                    k6,
                    "run",
                    "-e", f"VUS={users}",
                    "-e", f"BASE_URL={base}",
                    "-e", f"P95_MS={args.p95}",
                    "-e", f"MAX_FAIL={args.max_fail}",
                    "-e", f"WARMUP={args.warmup}s",
                    "-e", f"MEASURE={args.measure}s",
                    f"--summary-export={summary_file}",
                    "scripts/perf_register.js",
                ]

                print("running:", " ".join(k6_command), flush=True)

                result = subprocess.run(
                    k6_command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    shell=False,
                    check=False,
                )

                output = result.stdout + result.stderr
                output_file = OUT / f"k6-{users}u-run{run}.txt"
                output_file.write_text(output, encoding="utf-8")

                summary = json.loads(summary_file.read_text(encoding="utf-8"))

                row = summarise_run(
                    summary,
                    args.measure,
                    args.p95,
                    args.max_fail * 100,
                    parse_readback(output),
                )

                rows.append((users, run, row))

                print(
                    f"  p95 {row['p95_ms']:.0f} ms, "
                    f"{row['req_per_s']:.1f} req/s, "
                    f"{row['failed_pct']:.2f} % failed"
                )

                if result.returncode != 0:
                    print(f"k6 exited with status {result.returncode}")
                    return result.returncode

            finally:
                if server.poll() is None:
                    server.terminate()
                    server.wait(timeout=20)

    lines = [
        f"Limits: p95 < {args.p95} ms, unexpected failures < "
        f"{args.max_fail * 100:g} %. Measured phase {args.measure} s "
        f"after a {args.warmup} s warm-up.\n",
        "| Users | Run | p95 (ms) | Requests/s | Failed (%) | Registered | Read-back matches | Within limits |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for users, run, row in rows:
        readback = {True: "yes", False: "NO", None: "n/a"}[
            row.get("readback_ok")
        ]

        within_limits = (
            row["p95_ok"]
            and row["fail_ok"]
            and row.get("readback_ok") is True
        )

        lines.append(
            f"| {users} | {run} | {row['p95_ms']:.0f} | "
            f"{row['req_per_s']:.1f} | {row['failed_pct']:.2f} | "
            f"{row['registered_ok']} | {readback} | "
            f"{'yes' if within_limits else 'NO'} |"
        )

    report = "\n".join(lines) + "\n"
    (OUT / "results.md").write_text(report, encoding="utf-8")

    print("\n" + report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
