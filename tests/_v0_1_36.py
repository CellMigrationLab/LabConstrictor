"""Helper of the tests: a live template file as it was before template 0.1.36.

Template 0.1.36 no longer calls the napari, Fiji and QuPath plugins experimental (tools_bridge.md, the docs README, README.md) and removes
use_cases.md with the "Examples" section of the docs README and the README line that linked it. The tests of the older migrations compare
with the live files:

* `template_bytes` gives the bytes of a live template file, or of the frozen 0.1.35 copy for a file that 0.1.36 removed;
* `before_0_1_36` gives those bytes without the 0.1.36 edits (the migration's own edits undone).

The 0.1.36 changes are tested in test_template_sync_0_1_36.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_35_to_v0_1_36.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_36_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def template_bytes(relative: Path | str) -> bytes:
    """The live template file at `relative`; for a file 0.1.36 removed, the 0.1.35 template file it removed."""
    relative = Path(relative)
    if relative in _migration().REMOVED_FILES and not (ROOT / relative).exists():
        return (_migration().PREVIOUS_ROOT / relative).read_bytes()
    return (ROOT / relative).read_bytes()


def before_0_1_36(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the edits 0.1.36 made to it; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    if relative not in migration.EDITS:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in reversed(migration.EDITS[relative]):
        text = text.replace(new, old, 1)
    return text.replace("\n", newline).encode("utf-8")
