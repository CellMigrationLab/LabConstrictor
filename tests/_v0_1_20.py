"""Helper of the tests: a live template file as it was before template 0.1.20.

The resources of the older migrations are frozen: they are what those migrations deliver. Their tests compare them with the live template
files, and since 0.1.20 those files carry the lock-file lines (post_install.sh / .bat) or are new files (the two workflows). `before_0_1_20`
gives the bytes of the live file without the 0.1.20 change, so those tests keep checking what they checked; the 0.1.20 changes have their
own tests (test_template_sync_0_1_20.py). It also takes out the later changes to the files those resources hold: the check_placeholders.py
lines that 0.1.23 adds to release_constructor.yml (tested in test_template_sync_0_1_23.py), and every change of 0.1.24 (tests/_v0_1_24.py).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from _v0_1_24 import before_0_1_24

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_19_to_v0_1_20.py"
RELEASE_WORKFLOW = Path(".github/workflows/release_constructor.yml")
# The step 0.1.23 adds after bump_Welcome_notebook.py in both jobs of release_constructor.yml (five lines, any log path).
CHECK_STEP_0_1_23 = re.compile(
    r"[ ]+bash \.tools/bash/run_with_context\.sh \\\n"
    r"[ ]+\S+ \\\n"
    r"[ ]+\"check_placeholders\.py\" \\\n"
    r"[ ]+\.tools/python/check_placeholders\.py \\\n"
    r"[ ]+python \.tools/python/check_placeholders\.py\n"
)


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
    data = before_0_1_24(relative, data)
    if relative in migration.REPLACED_FILES:
        return (migration.PREVIOUS_ROOT / relative).read_bytes()
    if relative == RELEASE_WORKFLOW:
        return _without_placeholder_check(data)
    blocks = {migration.POST_INSTALL_SH: migration.SH_BLOCKS, migration.POST_INSTALL_BAT: migration.BAT_BLOCKS}.get(relative)
    if blocks is None:
        return data
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    for old, new in blocks:
        text = text.replace(new, old)
    return text.replace("\n", newline).encode("utf-8")


def _without_placeholder_check(data: bytes) -> bytes:
    """release_constructor.yml without the check_placeholders.py step of 0.1.23."""
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return CHECK_STEP_0_1_23.sub("", text.replace("\r\n", "\n")).replace("\n", newline).encode("utf-8")
