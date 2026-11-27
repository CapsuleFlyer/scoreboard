"""Server for the k6 load tests: fresh throw-away database, one tournament that never fills up.

    python scripts/perf_server.py --port 5056

Seeds tournament code PERF01 with room for a million teams, so the only limits hit are the
application's own. Uses the same threaded Werkzeug server as the browser tests (the performance
numbers therefore describe this development server with SQLite, and the report must say so).
The database is deleted when the process stops, so every run starts from the same data.
"""
import argparse
import logging
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import werkzeug.serving  # noqa: E402,F401
from werkzeug.serving import make_server  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Tournament  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5056)
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="perf-server-"))

    class Cfg:
        SECRET_KEY = "perf-secret-key"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp / 'perf.db').as_posix()}"
        WTF_CSRF_ENABLED = True

    app = create_app(Cfg)
    with app.app_context():
        db.session.add(Tournament(name="Perf Cup", registration_code="PERF01", max_teams=1_000_000))
        db.session.commit()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)     # request logging would distort the timings
    server = make_server("127.0.0.1", args.port, app, threaded=True)
    print(f"READY http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
