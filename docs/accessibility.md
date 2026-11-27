# Usability and accessibility evaluation (area 3)

## Run the tests (PowerShell)
```
python -m pip install -r requirements-e2e.txt
python -m playwright install chromium
python -m pytest tests/team/e2e -v --junitxml=docs/evidence/e2e/junit.xml
```
`E2E_SHOTS=1` (set `$env:E2E_SHOTS="1"` first) saves screenshots to `docs/evidence/e2e/screens/`. Failed tests save a screenshot automatically. The browser tests are skipped when Playwright is not installed.

## axe-core (before)
```
$env:A11Y_LABEL="before"; python -m pytest tests/team/e2e/test_e2e_accessibility.py -s
```
Reports: `docs/evidence/accessibility/before/*.json`. The test uses `axe-playwright-python` (the same axe-core engine as `@axe-core/playwright`). If your marker insists on the npm package, say so in the report or ask the TA.

## Lighthouse (before)
Needs Node. In one window `python scripts/e2e_server.py`; in another:
```
npx lighthouse http://127.0.0.1:5055/register/tournament/REG001 --only-categories=accessibility,best-practices,seo --output=json --output=html --output-path=docs/evidence/lighthouse/before/register-form
npx lighthouse http://127.0.0.1:5055/admin/tournament/1/registrations --extra-headers=lh-headers.json --only-categories=accessibility,best-practices,seo --output=json --output=html --output-path=docs/evidence/lighthouse/before/admin-registrations
```
`lh-headers.json` is written by `e2e_server.py` and holds a login cookie: do not commit it (add it to `.gitignore`).

## Findings table (fill in from the scans; an issue found by both tools counts once)
| # | Screen | Element | Rule / tool | User impact | Proposed fix | Status |
|---|---|---|---|---|---|---|
| 1 | TODO | TODO | TODO | TODO | TODO | TODO |

Observed in the browser run of 2026-11-27 (Playwright aria snapshot of the registration form, RUN): the team-name textbox is named only by its placeholder (`textbox "Enter team name"`) and the visible label "Team Name *" is plain text next to it, so the label is not associated with the input. Icons are read as private-use characters in link and button names (`"\uf3e5 Admin"`, `"\uf26b Register Team"`). The alert's close button has no accessible name (`button` with no text).

Fix made in this repository (screen: public registration form and code entry page): `for`/`id` on every label and input, `aria-describedby` for the character counters, `aria-label` on the code input and on the alert close buttons. Rerun the scans as `after` (below) and compare.

Hypotheses from reading the templates, to CONFIRM or drop with the scan (not findings yet):
- `register/tournament.html` and `register/index.html`: labels have no `for` and inputs have no `id`; the code input on the entry page has only a placeholder. Expected effect: screen readers cannot name the fields.
- Flash messages use `role="alert"` already; check the colour contrast of text on the dark theme.
- The navigation dropdown trigger is a link with `href="#"`.

## Fix one screen, rerun, compare
After choosing the screen (suggestion: the public registration form), change the template, then:
```
$env:A11Y_LABEL="after"; python -m pytest tests/team/e2e/test_e2e_accessibility.py -s
python scripts/a11y_compare.py register-form
```
and rerun the two Lighthouse commands into `.../after/`. The tests in `tests/team/e2e/` must still pass after the fix: they select inputs by `name`, so adding `id`/`for` does not break them.
