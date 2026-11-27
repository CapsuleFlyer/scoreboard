"""Start the app on a throw-away database with demo data, for Lighthouse, OWASP ZAP and k6.

    python scripts/e2e_server.py            # http://127.0.0.1:5055, Ctrl+C to stop

Seeds: admin "e2eadmin" / "e2e-pass-123", tournament "Spring Cup" (code REG001) with one confirmed
and one pending team. Prints the URLs and writes lh-headers.json (a logged-in session cookie) so
Lighthouse can scan admin pages:
    npx lighthouse http://127.0.0.1:5055/admin/tournament/1/registrations --extra-headers=lh-headers.json
CSRF is ON, like production. The database file is deleted when the script stops.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import werkzeug.serving  # noqa: E402,F401
from flask.sessions import SecureCookieSessionInterface  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Admin, Team, Tournament  # noqa: E402

PORT = 5055


def main():
    tmp = Path(tempfile.mkdtemp(prefix="e2e-server-"))

    class Cfg:
        SECRET_KEY = "demo-secret-key"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp / 'demo.db').as_posix()}"
        WTF_CSRF_ENABLED = True

    app = create_app(Cfg)
    with app.app_context():
        admin = Admin(username="e2eadmin")
        admin.set_password("e2e-pass-123")
        t = Tournament(name="Spring Cup", registration_code="REG001", max_teams=16, require_confirmation=True)
        db.session.add_all([admin, t])
        db.session.commit()
        db.session.add_all([
            Team(name="Alpha", player1="Ann", player2="Bob", tournament_id=t.id, is_confirmed=True),
            Team(name="Beta", player1="Cy", player2="Di", tournament_id=t.id, is_confirmed=False)])
        db.session.commit()
        admin_id, tid = admin.id, t.id
    serializer = SecureCookieSessionInterface().get_signing_serializer(app)
    cookie = serializer.dumps({"admin_id": admin_id, "admin_username": "e2eadmin"})
    headers = ROOT / "lh-headers.json"
    headers.write_text(json.dumps({"Cookie": f"{app.config['SESSION_COOKIE_NAME']}={cookie}"}), encoding="utf-8")
    base = f"http://127.0.0.1:{PORT}"
    print(f"Server: {base}   (Ctrl+C to stop)")
    print(f"  public code page   {base}/register/")
    print(f"  public form        {base}/register/tournament/REG001")
    print(f"  admin login        {base}/login")
    print(f"  admin registrations (needs lh-headers.json) {base}/admin/tournament/{tid}/registrations")
    print(f"Wrote {headers} (a logged-in session cookie; do not commit it)")
    server = make_server("127.0.0.1", PORT, app, threaded=True)
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
        headers.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
