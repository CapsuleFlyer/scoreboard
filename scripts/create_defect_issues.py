"""Create GitHub Issues from docs/defect-drafts.md using the GitHub CLI (gh).

Usage (from the repo root):
    python scripts/create_defect_issues.py            # dry run: prints what would be created
    python scripts/create_defect_issues.py --create   # really creates the issues

Needs: gh installed and logged in (gh auth login), and the labels from
docs/defect-management.md already created in the repository.
Writes docs/defect-issue-map.md (draft ID -> issue URL) after creating.
Refuses to run twice (so issues are not duplicated) if that file exists.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "CapsuleFlyest/scoreboard"
ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "docs" / "defect-drafts.md"
MAPFILE = ROOT / "docs" / "defect-issue-map.md"

HEADER = re.compile(r"^## (DR-\d+) (.+)$", re.MULTILINE)
CLASS = re.compile(
    r"Severity:\s*(\w+).*?Priority:\s*(P\d).*?Category:\s*([\w-]+)", re.DOTALL
)


def parse_drafts(text):
    """Return a list of dicts: id, title, body, labels."""
    matches = list(HEADER.finditer(text))
    drafts = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end():end].strip().rstrip("-").strip()
        c = CLASS.search(block)
        if not c:
            raise ValueError(f"{m.group(1)}: could not find Severity/Priority/Category line")
        severity, priority, category = c.groups()
        drafts.append({
            "id": m.group(1),
            "title": f"[DEFECT] {m.group(2).strip()}",
            "body": f"Draft ID: {m.group(1)}\n\n{block}\n",
            "labels": [
                "type:defect",
                "status:new",
                f"severity:{severity}",
                f"priority:{priority}",
                f"cat:{category}",
            ],
        })
    return drafts


def main():
    create = "--create" in sys.argv
    drafts = parse_drafts(DRAFTS.read_text(encoding="utf-8"))
    print(f"Found {len(drafts)} drafts in {DRAFTS.name}")

    if not create:
        for d in drafts:
            print(f"- {d['id']}: {d['title']}\n    labels: {', '.join(d['labels'])}")
        print("\nDry run only. Re-run with --create to create the issues.")
        return 0

    if MAPFILE.exists():
        print(f"{MAPFILE.name} already exists, so issues were already created. Stopping to avoid duplicates.")
        return 1
    gh = shutil.which("gh")
    if not gh:
        print("gh was not found on PATH. Install it and run: gh auth login")
        return 1

    rows = []
    for d in drafts:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(d["body"])
            body_path = f.name
        cmd = [gh, "issue", "create", "--repo", REPO, "--title", d["title"], "--body-file", body_path]
        for label in d["labels"]:
            cmd += ["--label", label]
        result = subprocess.run(cmd, capture_output=True, text=True)
        Path(body_path).unlink(missing_ok=True)
        if result.returncode != 0:
            print(f"FAILED {d['id']}: {result.stderr.strip()}")
            print("Stopping. Fix the problem (usually a missing label), then see below.")
            break
        url = result.stdout.strip().splitlines()[-1]
        print(f"{d['id']} -> {url}")
        rows.append((d["id"], d["title"], url))

    if rows:
        lines = ["# Defect issue map", "", "| Draft | Title | Issue |", "|---|---|---|"]
        lines += [f"| {i} | {t} | {u} |" for i, t, u in rows]
        MAPFILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote {MAPFILE.name} with {len(rows)} rows.")
        if len(rows) < len(drafts):
            print("Only some drafts were created. Do NOT rerun --create; create the rest by hand to avoid duplicates.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
