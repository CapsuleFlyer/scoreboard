"""Accessibility scan of the key screens with axe-core (via axe-playwright-python, same engine as
@axe-core/playwright). Writes one JSON report per screen under docs/evidence/accessibility/<label>/
where <label> is the A11Y_LABEL environment variable (default "before"). Run it again with
A11Y_LABEL=after once a screen is fixed, then compare with scripts/a11y_compare.py.

The test only fails if a scan cannot run; it does not demand zero violations, because the point
is to record and prioritise what is found.
Status: written against the library's documented API (READ). Run on your machine first.
"""
import json
import os

import pytest

axe_module = pytest.importorskip("axe_playwright_python.sync_playwright")

from e2e_helpers import ROOT, admin_login  # noqa: E402

LABEL = os.environ.get("A11Y_LABEL", "before")
OUT = ROOT / "docs" / "evidence" / "accessibility" / LABEL


def scan(page, name):
    results = axe_module.Axe().run(page)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(results.response, indent=2), encoding="utf-8")
    return results.response["violations"]


def summarise(violations):
    return [(v["id"], v["impact"], len(v["nodes"])) for v in violations]


def test_scan_public_registration_form(world, page):
    world.tournament(name="Spring Cup")
    page.goto("/register/tournament/REG001")
    found = scan(page, "register-form")
    print("register-form:", summarise(found))
    assert isinstance(found, list)


def test_scan_code_entry_page(world, page):
    world.tournament()
    page.goto("/register/")
    found = scan(page, "register-index")
    print("register-index:", summarise(found))
    assert isinstance(found, list)


def test_scan_admin_login(world, page):
    page.goto("/login")
    found = scan(page, "admin-login")
    print("admin-login:", summarise(found))
    assert isinstance(found, list)


def test_scan_admin_registrations_page(world, page):
    tid = world.tournament()
    world.team(tid, "Alpha", confirmed=False)
    admin_login(page)
    page.goto(f"/admin/tournament/{tid}/registrations")
    found = scan(page, "admin-registrations")
    print("admin-registrations:", summarise(found))
    assert isinstance(found, list)
