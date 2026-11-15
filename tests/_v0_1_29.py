"""Helper of the tests: a live template file as it was before template 0.1.29.

Template 0.1.29 corrects texts in post_install.sh / .bat, tools_bridge.md, app_manifest.md, use_cases.md, the docs README and
update_changelog.py. The resources of the older migrations are frozen; `before_0_1_29` gives the bytes of a live file with those
corrections undone, using the migration's own pairs, so their tests keep checking what they checked. The design-note entries the
0.1.29 migration removes from the docs README are not put back. The corrections themselves are tested in test_template_sync_0_1_29.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_28_to_v0_1_29.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_29_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_29(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the corrections 0.1.29 made to it; any other file is returned as it is."""
    migration = _migration()
    edits = migration.EDITS.get(Path(relative))
    if not edits:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in reversed(edits):
        text = text.replace(new, old, 1)
    return text.replace("\n", newline).encode("utf-8")
