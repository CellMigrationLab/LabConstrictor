"""Helper of the tests: a live template file as it was before template 0.1.33.

Template 0.1.33 moves the Tools pin (`LC_TOOLS_PIN` in post_install.sh / .bat) from v0.3.0-alpha.2 to v0.3.0-alpha.3. The tests of the older
migrations compare with the live files; `before_0_1_33` gives the bytes of a live file with the pin moved back, so they keep checking what they
checked. The move itself is tested in test_template_sync_0_1_33.py.
"""
from __future__ import annotations

from pathlib import Path

PIN_0_1_28 = "v0.3.0-alpha.2"
PIN_0_1_33 = "v0.3.0-alpha.3"
PINNED_FILES = (Path("app/bash_bat_scripts/post_install.sh"), Path("app/bash_bat_scripts/post_install.bat"))


def before_0_1_33(relative: Path | str, data: bytes) -> bytes:
    """`data` (a live template file at `relative`) with the 0.1.33 pin moved back; any other file is returned as it is."""
    if Path(relative) not in PINNED_FILES:
        return data
    return data.replace(PIN_0_1_33.encode(), PIN_0_1_28.encode())
