"""Helper of the tests: a live template file as it was before template 0.1.25.

The resources of the older migrations are frozen (they are what those migrations deliver), and their tests compare them with the live
template files. Of those files, 0.1.25 changed only bump_version.py (the release writes its version into setup.py): `before_0_1_25` undoes
exactly the blocks the 0.1.25 migration adds, using the migration's own constants, so those tests keep checking what they checked. setup.py
is not a resource of an older migration; the 0.1.25 changes have their own tests (test_template_sync_0_1_25.py).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_24_to_v0_1_25.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_25_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_25(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the change 0.1.25 made to it; any other file is returned as it is."""
    migration = _migration()
    if Path(relative) != migration.BUMP_VERSION:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in reversed(migration.BUMP_BLOCKS):
        text = text.replace(new, old, 1)
    return text.replace("\n", newline).encode("utf-8")
