"""Shared constants and helpers for the browser tests (importable from the test files)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs" / "evidence" / "e2e"
ADMIN_USER, ADMIN_PASSWORD = "e2eadmin", "e2e-pass-123"


def admin_login(page, username=ADMIN_USER, password=ADMIN_PASSWORD):
    page.goto("/login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.click("button[type=submit]")
