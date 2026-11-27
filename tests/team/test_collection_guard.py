"""Guards the test layout: pytest (without __init__.py files) cannot import two test modules with the
same file name, so a bare `pytest` or `pytest tests/` fails at collection with "import file mismatch"
and runs nothing. This happened when two files in tests/team reused the names of upstream tests.
Pure standard library: no Flask, no database."""
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]


def test_no_two_test_modules_share_a_file_name():
    seen = {}
    for path in TESTS.rglob("test_*.py"):
        seen.setdefault(path.name, []).append(path.relative_to(TESTS.parent).as_posix())
    clashes = {name: paths for name, paths in seen.items() if len(paths) > 1}
    assert not clashes, f"duplicate test module names (rename one of each pair): {clashes}"
