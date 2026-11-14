"""Helper of the tests: a live template file as it was before template 0.1.28.

Template 0.1.28 moves the Tools pin (`LC_TOOLS_PIN` in post_install.sh / .bat, and the tag named in tools_bridge.md) from v0.3.0-alpha.1 to
v0.3.0-alpha.2. The resources of the older migrations are frozen and hold the old pin; `before_0_1_28` gives the bytes of a live file with the
pin moved back, so their tests keep checking what they checked. The move itself is tested in test_template_sync_0_1_28.py.
"""
from __future__ import annotations

from pathlib import Path

PIN_0_1_18 = "v0.3.0-alpha.1"  # the pin 0.1.18 introduced
PIN_0_1_28 = "v0.3.0-alpha.2"
PINNED_FILES = (Path("app/bash_bat_scripts/post_install.sh"), Path("app/bash_bat_scripts/post_install.bat"), Path(".tools/docs/tools_bridge.md"))


def before_0_1_28(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) with the 0.1.28 pin moved back; any other file is returned as it is."""
    if Path(relative) not in PINNED_FILES:
        return data
    return data.replace(PIN_0_1_28.encode(), PIN_0_1_18.encode())
