# Defensive security assessment (area 3, DRAFT)

Scope: the two registered workflows, on the local copy, with synthetic data only.

## Attack surface (routes and data)
| Workflow | Route | Method | Who | Data read or changed |
|---|---|---|---|---|
| W1 | `/register/`, `/register/join`, `/register/tournament/<code>`, `/register/team`, `/register/success/...` | GET, POST | visitor | tournament (by code), Team rows, count vs `max_teams` |
| W1 | `/api/register/validate-code`, `/api/register/team` | POST (JSON) | visitor, CSRF-exempt | same |
| W2 | `/admin/tournament/<id>/registrations`, `.../team/<id>/confirm`, `/reject`, `/checkin`, `/team/add`, `/registration/toggle` | GET, POST | admin | Team rows, tournament registration flag |
| both | `/login`, `/logout` | GET, POST | visitor, admin | session cookie (`admin_id`) |

## Roles and expected decisions
Visitor: may use W1 only. Admin: W2 plus everything a visitor may do. The recorded decisions are in `docs/evidence/security/access-matrix.csv` after you run the tests (role, action, expected, observed, evidence). Nothing in this file is a result until you have run them.

## Run (PowerShell)
```
python -m pytest tests/team/e2e/test_security_access.py -v
```
Outputs: `docs/evidence/security/access-matrix.csv` (at least ten rows over two roles, allowed and denied) and `controls.csv` (cookie attributes, CSRF behaviour, header presence).

## OWASP ZAP in passive mode while the browser tests run
1. Install ZAP (desktop app) and start it with the proxy on port 8090: `zap.bat -daemon -port 8090 -config api.disablekey=true` (do not run the spider or active scan: passive only).
2. In PowerShell: `$env:E2E_PROXY="http://127.0.0.1:8090"` then `python -m pytest tests/team/e2e -v`. The browser sends all traffic through ZAP (loopback is forced through the proxy by the conftest).
3. Export the alerts: `Invoke-RestMethod http://127.0.0.1:8090/JSON/core/view/alerts/ | ConvertTo-Json -Depth 10 | Out-File docs/evidence/security/zap-alerts.json`
4. Clear the variable: `Remove-Item Env:E2E_PROXY`.
Record per alert: affected URL, evidence, likely impact, recommended fix.

## Dependency audit
Run on Windows so the report shows the versions of your own environment:
```
python -m pip install pip-audit
python -m pip freeze > docs/evidence/security/pip-freeze.txt
pip-audit -r requirements.txt -f json -o docs/evidence/security/pip-audit-windows.json
```
Record for each relevant vulnerability: package, installed version, advisory id, likely impact, fix version. The Linux audit in DR-10 found 14 unique advisories; compare.

## Controls verified from the source (READ, confirm by running)
- CSRF: `CSRFProtect` is global (`app/__init__.py` line 9); exempt: `api`, `external_api`, `input_bp` (lines 43 to 45). Forms and the admin `fetch` calls send the token.
- Authentication: `login_required` (`app/blueprints/auth.py`) on all admin routes; passwords are hashed with Werkzeug.
- Session cookie: no `SESSION_COOKIE_*` setting in `config.py`, so Flask defaults apply (HttpOnly on, Secure off, SameSite not set). Confirm with `controls.csv`.
- Security headers: none found in the source (`after_request`, CSP, Talisman). Confirm with `controls.csv`.
- The login redirect checks the host of `next` (open-redirect guard), tested in `test_auth_input_display.py`.

## Findings to evaluate (candidates, not confirmed until you have the evidence)
| Candidate | Evidence needed | Related |
|---|---|---|
| API blueprint accepts registrations without CSRF token or rate limit | `controls.csv` row, DR-12 | R? in `docs/risk-register.md` |
| Missing security headers | `controls.csv` row, ZAP alert | |
| Session cookie without Secure/SameSite | `controls.csv` row | |
| Timer and display-mode endpoints without login | DR-17 | |
