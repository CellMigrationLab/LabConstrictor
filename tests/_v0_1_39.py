"""Helper of the tests: a live template file as it was before template 0.1.39.

Template 0.1.39 replaces two guides in .tools/docs whole (FILES of the migration). The tests of the older migrations compare with
the live files; `before_0_1_39` gives the bytes of a live file without the 0.1.39 change (the frozen 0.1.38 copy when the file is the 0.1.39
page), so they keep checking what they checked. The 0.1.39 changes are tested in test_template_sync_0_1_39.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from _v0_1_40 import before_0_1_40

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_38_to_v0_1_39.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_39_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_39(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the 0.1.39 change; any other file is returned as it is."""
    data = before_0_1_40(relative, data)
    migration = _migration()
    relative = Path(relative)
    if relative not in migration.FILES:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    # Only the 0.1.39 page is swapped back: older helpers may run this chain again on text that is already older.
    if text.replace("\r\n", "\n") != (migration.RESOURCE_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n"):
        return data
    previous = (migration.PREVIOUS_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n")
    return previous.replace("\n", newline).encode("utf-8")
