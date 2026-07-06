from __future__ import annotations

from pathlib import Path
from typing import Any
import re


BUMP_CONSTRUCTOR_PATH = Path(".tools/python/bump_constructor.py")


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def update_bump_constructor(repo_root: Path) -> bool:
    path = repo_root / BUMP_CONSTRUCTOR_PATH
    if not path.exists():
        print(f"Skipping missing file: {BUMP_CONSTRUCTOR_PATH}")
        return False

    original_text = read_text(path)
    newline = detect_newline(original_text)

    updated_block = newline.join(
        [
            "        normalized_items.append({setup_src: setup_dst})",
            "        src_added += 1",
            '        debug(f"Included setup.py: {setup_src} -> {setup_dst}")',
        ]
    )

    if updated_block in original_text and 'if setup_src not in existing_sources and setup_dst not in existing_dests:' not in original_text:
        return False

    patterns = [
        re.compile(
            r'        if setup_src not in existing_sources and setup_dst not in existing_dests:\r?\n'
            r'            normalized_items\.append\(\{setup_src: setup_dst\}\)\r?\n'
            r'            src_added \+= 1\r?\n'
            r'(?:            debug\(f"Included setup\.py: \{setup_src\} -> \{setup_dst\}"\)\r?\n)?'
            r'        else:\r?\n'
            r'(?:            debug\("setup\.py mapping already present"\)\r?\n)?'
        ),
        re.compile(
            r'        if setup_src not in existing_sources and setup_dst not in existing_dests:\r?\n'
            r'            normalized_items\.append\(\{setup_src: setup_dst\}\)\r?\n'
            r'            src_added \+= 1\r?\n'
        ),
    ]

    replacement = updated_block + newline
    updated_text = original_text
    changed = False

    for pattern in patterns:
        updated_text, replacements = pattern.subn(replacement, updated_text, count=1)
        if replacements:
            changed = True
            break

    if not changed:
        raise ValueError(f"Unable to find setup.py conditional block in {BUMP_CONSTRUCTOR_PATH}")

    write_text(path, updated_text)
    print(f"Updated {BUMP_CONSTRUCTOR_PATH}")
    return True


def migrate(repo_root: Path, context: dict[str, Any]) -> None:
    _ = context

    changed_any = False
    changed_any = update_bump_constructor(repo_root) or changed_any

    if not changed_any:
        print("No repository changes were required for this migration.")
