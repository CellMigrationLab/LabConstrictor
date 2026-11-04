"""Helper of the tests: a live template file as it was before template 0.1.20.

The resources of the older migrations are frozen: they are what those migrations deliver. Their tests compare them with the live template
files, and since 0.1.20 those files carry the lock-file lines (post_install.sh / .bat) or are new files (the two workflows). `before_0_1_20`
gives the bytes of the live file without the 0.1.20 change, so those tests keep checking what they checked; the 0.1.20 changes have their
own tests (test_template_sync_0_1_20.py).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_19_to_v0_1_20.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_20_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_20(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the change 0.1.20 made to it; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    if relative in migration.REPLACED_FILES:
        return (migration.PREVIOUS_ROOT / relative).read_bytes()
    blocks = {migration.POST_INSTALL_SH: migration.SH_BLOCKS, migration.POST_INSTALL_BAT: migration.BAT_BLOCKS}.get(relative)
    if blocks is None:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in blocks:
        text = text.replace(new, old)
    return text.replace("\n", newline).encode("utf-8")
