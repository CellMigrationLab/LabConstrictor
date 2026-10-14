"""Helper of the tests: the template post_install scripts without the app-hosts lines (the step added in 0.1.18 after the pin step).

Tests of the pin step, and of the frozen 0.1.17 resources, compare scripts with the older shape; `strip_hosts` removes exactly the lines
the hosts step adds, so those tests keep checking what they checked, and the hosts step has its own tests (test_template_sync_0_1_18_hosts.py).
"""
from __future__ import annotations

import re


SH_START = "# Hosts of the app:"
SH_ARGS = ' ${LC_HOSTS_ARGS[@]+"${LC_HOSTS_ARGS[@]}"}'
BAT_PRE_START = "REM Hosts of the app:"
BAT_PRE_LAST = 'IF DEFINED LC_APP_MANIFEST findstr'
BAT_LOGS_START = "    REM Which hosts list the app"
BAT_LOG_LINE = re.compile(r"^    IF (NOT )?DEFINED LC_APP_MANIFEST (IF (NOT )?DEFINED LC_APP_HAS_HOSTS )?echo ")


def _drop_range(lines: list[str], start: str, last: str) -> list[str]:
    """Remove the lines from the first one that starts with `start` up to and including the next one that starts with `last`."""
    begin = next((i for i, line in enumerate(lines) if line.startswith(start)), None)
    if begin is None:
        return lines
    stop = next(i for i in range(begin, len(lines)) if lines[i].startswith(last))
    return lines[:begin] + lines[stop + 1 :]


def strip_hosts_sh(text: str) -> str:
    """Remove the inserted block: from its first comment line to the `fi` that closes it (same indent as the comment), and the register argument."""
    lines = text.split("\n")
    begin = next((i for i, line in enumerate(lines) if line.lstrip().startswith(SH_START)), None)
    if begin is not None:
        indent = lines[begin][: len(lines[begin]) - len(lines[begin].lstrip())]
        stop = next(i for i in range(begin, len(lines)) if lines[i].rstrip("\r") == indent + "fi")
        lines = lines[:begin] + lines[stop + 1 :]
    return "\n".join(lines).replace(SH_ARGS, "")


def strip_hosts_bat(text: str) -> str:
    lines = _drop_range(text.split("\n"), BAT_PRE_START, BAT_PRE_LAST)
    lines = [line for line in lines if not line.startswith(BAT_LOGS_START) and not BAT_LOG_LINE.match(line.rstrip("\r"))]
    lines = [line for line in lines if " IF NOT DEFINED LC_APP_MANIFEST " not in line]
    return "\n".join(line.replace(" IF DEFINED LC_APP_MANIFEST ", " ").replace(' --app-manifest "%LC_APP_MANIFEST%"', "") for line in lines)


def strip_hosts(name: str, data: bytes) -> bytes:
    """The script `name` (post_install.sh or post_install.bat) as bytes, without the lines of the hosts step (line endings kept)."""
    strip = strip_hosts_sh if name.endswith(".sh") else strip_hosts_bat
    return strip(data.decode()).encode()
