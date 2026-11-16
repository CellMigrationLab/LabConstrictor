"""Helper of the tests: a live template file as it was before template 0.1.32.

Template 0.1.32 rewrote tools_bridge.md around what the template owns (it links to the owner guides of the plugins and of LabConstrictor
Tools), and changed one paragraph of install.md and one entry of the docs README. The resources of the older migrations are frozen;
`before_0_1_32` gives the bytes of a live file without the 0.1.32 change (the frozen 0.1.31 copy for tools_bridge.md, the migration's own
edits undone for the others), so their tests keep checking what they checked. The 0.1.32 changes are tested in test_template_sync_0_1_32.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_31_to_v0_1_32.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_32_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_32(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the change 0.1.32 made to it; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    if relative not in migration.FILES:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    if relative in migration.WHOLE_FILES:
        # Only the 0.1.32 file is swapped back: older helpers run this chain again on text that is already older (tests/_v0_1_20.py).
        if text.replace("\r\n", "\n") != (migration.RESOURCE_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n"):
            return data
        text = (migration.PREVIOUS_ROOT / relative).read_bytes().decode("utf-8").replace("\r\n", "\n")
    else:
        text = text.replace("\r\n", "\n")
        for old, new in reversed(migration.EDITS[relative]):
            text = text.replace(new, old, 1)
    return text.replace("\n", newline).encode("utf-8")
