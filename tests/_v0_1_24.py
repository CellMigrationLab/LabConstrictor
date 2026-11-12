"""Helper of the tests: a live template file as it was before template 0.1.24.

The resources of the older migrations are frozen (they are what those migrations deliver), and their tests compare them with the live
template files. 0.1.24 changed three of those files (bump_version.py, release_constructor.yml, launch_jupyter.py): `before_0_1_24` undoes
exactly the blocks the 0.1.24 migration adds, using the migration's own constants, so those tests keep checking what they checked. The
0.1.24 changes have their own tests (test_template_sync_0_1_24.py), which also check that migrating these 0.1.23 files gives the 0.1.24
ones. The later change of 0.1.25 to bump_version.py is taken out first (tests/_v0_1_25.py).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from _v0_1_25 import before_0_1_25

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_23_to_v0_1_24.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_24_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def undo_blocks(text_lf: str, blocks: tuple[tuple[str, str], ...]) -> str:
    for old, new in reversed(blocks):
        text_lf = text_lf.replace(new, old, 1)
    return text_lf


def workflow_before_0_1_24(text_lf: str) -> str:
    migration = _migration()
    text_lf = text_lf.replace(migration.MATRIX_NEW, migration.MATRIX_OLD, 1).replace(migration.PLATFORMS_JOB, "", 1)
    tag_lines = re.escape(migration.TAG_LINES).replace(re.escape("{indent}"), "[ ]+")
    return re.sub(tag_lines, "", text_lf)


def before_0_1_24(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the change 0.1.24 made to it; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    data = before_0_1_25(relative, data)
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    if relative == migration.BUMP_VERSION:
        text = undo_blocks(text, migration.BUMP_BLOCKS)
    elif relative == migration.LAUNCHER:
        text = undo_blocks(text, (migration.LAUNCHER_BLOCK,))
    elif relative == migration.RELEASE_WORKFLOW:
        text = workflow_before_0_1_24(text)
    else:
        return data
    return text.replace("\n", newline).encode("utf-8")
