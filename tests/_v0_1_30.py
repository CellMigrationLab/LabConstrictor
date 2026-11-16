"""Helper of the tests: a live template file as it was before template 0.1.30.

Template 0.1.30 changes the website's address in app_manifest.md, install.md, the schema copy and its README, the VLab4Mic logo address
in use_cases.md and one sentence of tools_bridge.md. The resources of the older migrations are frozen; `before_0_1_30` gives the bytes of
a live file with those changes undone, so their tests keep checking what they checked. The changes themselves are tested in
test_template_sync_0_1_30.py. The later changes of 0.1.31 are taken out first (tests/_v0_1_31.py).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from _v0_1_31 import before_0_1_31

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_29_to_v0_1_30.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_30_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_30(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the changes 0.1.30 made to it; any other file is returned as it is."""
    data = before_0_1_31(relative, data)
    migration = _migration()
    relative = Path(relative)
    if relative in migration.ADDRESS_FILES:
        return data.replace(migration.NEW_URL.encode(), migration.OLD_URL.encode())
    edits = migration.EDITS.get(relative)
    if not edits:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in reversed(edits):
        text = text.replace(new, old, 1)
    return text.replace("\n", newline).encode("utf-8")


def live_0_1_29(relative: Path | str) -> bytes:
    """The live template file at `relative` as template 0.1.29 had it."""
    return before_0_1_30(relative, (ROOT / relative).read_bytes())
