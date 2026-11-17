"""Helper of the tests: a live template file as it was before template 0.1.33.

Template 0.1.33 moves the Tools pin (`LC_TOOLS_PIN` in post_install.sh / .bat) from v0.3.0-alpha.2 to v0.3.0-alpha.3, and rewrites the
Windows Apps-list block of post_install.bat. The tests of the older migrations compare with the live files; `before_0_1_33` gives the bytes of
a live file with both changes undone, so they keep checking what they checked. The changes are tested in test_template_sync_0_1_33.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from _v0_1_34 import before_0_1_34

PIN_0_1_28 = "v0.3.0-alpha.2"
PIN_0_1_33 = "v0.3.0-alpha.3"
PINNED_FILES = (Path("app/bash_bat_scripts/post_install.sh"), Path("app/bash_bat_scripts/post_install.bat"))


MIGRATION_PATH = Path(__file__).resolve().parents[1] / ".template_sync/migrations/v0_1_32_to_v0_1_33.py"


def _apps_list_blocks() -> tuple[str, str, str, str]:
    """(new block, old block, new icon line, old icon line) of the template's post_install.bat, from the migration itself."""
    spec = importlib.util.spec_from_file_location("migration_0_1_33_for_older_tests", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    new = "\r\n".join(migration.NEW_ARP_LINES).replace("{version}", "VERSION_NUMBER")
    old = 'SET "DISPLAY_ICON=%PROJECT_ROOT%\\logo.ico"\r\nSET "DISPLAY_VERSION=VERSION_NUMBER"'
    return new, old, migration.NEW_ICON_REG, migration.OLD_ICON_REG


def before_0_1_33(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) with the 0.1.33 pin moved back and the old Apps-list block; any other file as it is."""
    data = before_0_1_34(relative, data)
    if Path(relative) not in PINNED_FILES:
        return data
    data = data.replace(PIN_0_1_33.encode(), PIN_0_1_28.encode())
    if Path(relative).suffix == ".bat":
        new, old, new_reg, old_reg = _apps_list_blocks()
        data = data.replace(new.encode(), old.encode()).replace(new_reg.encode(), old_reg.encode())
    return data
