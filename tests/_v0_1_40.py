"""Helper of the tests: a live template file as it was before template 0.1.40.

Template 0.1.40 replaces seven guides in .tools/docs whole (FILES of the migration). The tests of the older migrations compare with
the live files; `before_0_1_40` gives the bytes of a live file without the 0.1.40 change (the frozen 0.1.39 copy when the file is the 0.1.40
page), so they keep checking what they checked. The 0.1.40 changes are tested in test_template_sync_0_1_40.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_39_to_v0_1_40.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_40_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_40(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the 0.1.40 change; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    if relative not in migration.FILES:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    # Only the 0.1.40 page is swapped back: older helpers may run this chain again on text that is already older.
    if text.replace("\r\n", "\n") != (migration.RESOURCE_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n"):
        return data
    previous = (migration.PREVIOUS_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n")
    return previous.replace("\n", newline).encode("utf-8")
