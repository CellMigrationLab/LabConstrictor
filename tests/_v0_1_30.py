"""Helper of the tests: a live template file as it was before template 0.1.30.

Template 0.1.30 replaced merge_requirements.py, added packaging to .tools/requirements.txt, three lines to update_on_notebook_change.yml,
the requirements check to release_constructor.yml and the safe notebook update to Welcome_template.ipynb. The resources of the older
migrations are frozen; `before_0_1_30` gives the bytes of a live file without the 0.1.30 change, using the migration's own constants (the
frozen 0.1.29 copies for merge_requirements.py and the Welcome template), so their tests keep checking what they checked. The 0.1.30
changes are tested in test_template_sync_0_1_30.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_29_to_v0_1_30.py"
WELCOME_0_1_29 = ROOT / "tests/fixtures/template_0_1_29/Welcome_template.ipynb"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0_1_30_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def before_0_1_30(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) without the change 0.1.30 made to it; any other file is returned as it is."""
    migration = _migration()
    relative = Path(relative)
    if relative == migration.MERGE:
        return (migration.PREVIOUS_ROOT / migration.MERGE).read_bytes()
    if relative == migration.WELCOME_TEMPLATE:
        return WELCOME_0_1_29.read_bytes()
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    if relative == migration.TOOLS_REQUIREMENTS:
        text = text.replace(migration.PACKAGING_LINES, "", 1)
    elif relative == migration.NOTEBOOK_WORKFLOW:
        for old, new in reversed(migration.NOTEBOOK_WORKFLOW_BLOCKS):
            text = text.replace(new, old, 1)
    elif relative == migration.RELEASE_WORKFLOW:
        match = migration.PLACEHOLDER_STEP.search(text)
        if match is not None:
            step = migration.REQUIREMENTS_CHECK_STEP.format(indent=match.group("indent"), log=match.group("log"))
            if text[match.end() :].startswith(step):
                text = text[: match.end()] + text[match.end() + len(step) :]
    else:
        return data
    return text.replace("\n", newline).encode("utf-8")
