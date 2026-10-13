"""Template 0.1.17 -> 0.1.18: new Tools pin, GitHub Actions pinned by commit SHA, install rules in the install guide.

Design note: https://github.com/CellMigrationLab/LabConstrictor/blob/main/.tools/docs/migration_0_1_18.md

What this changes in an app repository (every step is independent, idempotent and never deletes anything):

1. Tools pin. `LC_TOOLS_PIN` in app/bash_bat_scripts/post_install.sh / .bat moves from the old template value `v0.2.0-rc.1` to the new one
   (read from the resource copy of the template script, `v0.3.0-alpha.1`), ONLY when the line still holds exactly the old template value.
   An app with its own pin, a script without a pin line (unpinned source, own `LC_TOOLS_SPEC`) or without the hook stays as it is, with a note.
2. Pinned actions. The five template workflows (check_app_manifest.yml, release_constructor.yml, sync_template.yml,
   update_on_notebook_change.yml, update_on_src_change.yaml) are replaced by the pinned version ONLY when the app's file is still identical to
   the previous template version (the resource with the pins removed; line endings are ignored when comparing and kept when writing).
   A file that already is the pinned template file is unchanged; a file that is customised (or pinned in part by the app) is skipped with a
   message that lists its still unpinned `uses:` lines. A workflow file that is not in the repository is not created.
3. Install guide. `.tools/docs/install.md`, if it exists, gets the section "Before you install" (path without a space) and the section
   "Update an installed app" (macOS/Windows uninstall first, Linux `-u`), inserted before "## Install on Windows" and before "## Next".
4. Tools guide. `.tools/docs/tools_bridge.md` is refreshed (it names the pinned tag) only if it still is the 0.1.17 text.

Rules this migration keeps: surgical (only known lines or known files), idempotent (a second run reports no changes), never raises for a
customised file (the sync pull request must still be created), the line endings of each file are kept, nothing is deleted.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any


RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "resources" / "v0_1_17_to_v0_1_18"
SCRIPTS = Path("app/bash_bat_scripts")
POST_INSTALL_SH = SCRIPTS / "post_install.sh"
POST_INSTALL_BAT = SCRIPTS / "post_install.bat"
TOOLS_DOC = Path(".tools/docs/tools_bridge.md")
INSTALL_DOC = Path(".tools/docs/install.md")
WORKFLOWS = (
    Path(".github/workflows/check_app_manifest.yml"),
    Path(".github/workflows/release_constructor.yml"),
    Path(".github/workflows/sync_template.yml"),
    Path(".github/workflows/update_on_notebook_change.yml"),
    Path(".github/workflows/update_on_src_change.yaml"),
)
# Resource files: copies of the template files of 0.1.18 (a test checks they stay identical to the template).
MANAGED_FILES = (POST_INSTALL_SH, POST_INSTALL_BAT, TOOLS_DOC, INSTALL_DOC, *WORKFLOWS)

DOCS_URL = "https://github.com/CellMigrationLab/LabConstrictor/blob/main/.tools/docs/migration_0_1_18.md"
TAG = "[migration 0.1.18]"
OLD_PIN = "v0.2.0-rc.1"
NEW_PIN_RE = re.compile(r'LC_TOOLS_PIN="([^"]+)"')

# The pinned third-party action lines, `uses: owner/repo@<40 hex> # <tag>`; removing the pin gives `uses: owner/repo@<tag>`.
PINNED_USES = re.compile(r"^(\s*(?:-\s+)?uses:\s*[\w.-]+/[\w./-]+)@[0-9a-f]{40}[ \t]+#[ \t]*(\S+)[ \t]*$")
ANY_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*([\w.-]+/[\w./-]+)@(\S+)")

INSTALL_BEFORE_HEADING = "## Before you install"
INSTALL_UPDATE_HEADING = "## Update an installed app"
INSTALL_BEFORE_ANCHOR = "## Install on Windows"
INSTALL_UPDATE_ANCHOR = "## Next"


def log(message: str) -> None:
    print(f"{TAG} {message}")


def _load_helpers() -> Any:
    """Reuse the helpers of the 0.1.10 migration (token replacement, newline detection, file IO)."""
    path = Path(__file__).resolve().parent / "v0_1_9_to_v0_1_10.py"
    spec = importlib.util.spec_from_file_location("template_sync_helpers_0_1_18", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resource_text(helpers: Any, relative: Path) -> str:
    source = RESOURCE_ROOT / relative
    if not source.is_file():
        raise FileNotFoundError(f"Template resource not found: {source}")
    return str(helpers.read_text(source)).replace("\r\n", "\n")


def new_pin(helpers: Any) -> str:
    """The pin of the template (the resource copy of post_install.sh is the single source of the value)."""
    match = NEW_PIN_RE.search(_resource_text(helpers, POST_INSTALL_SH))
    if not match:
        raise ValueError("LC_TOOLS_PIN was not found in the template resource")
    return match.group(1)


def _unpin(text: str) -> str:
    """The text of a workflow before its actions were pinned (the previous template version)."""
    lines = []
    for line in text.split("\n"):
        match = PINNED_USES.match(line)
        lines.append(f"{match.group(1)}@{match.group(2)}" if match else line)
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------------------------------------------
# 1. Tools pin
# --------------------------------------------------------------------------------------------------------------------------------
SH_PIN_LINE = re.compile(r'^([ \t]*LC_TOOLS_PIN=")([^"]*)(".*)$')
BAT_PIN_LINE = re.compile(r'^([ \t]*SET "LC_TOOLS_PIN=)([^"]*)(".*)$', re.IGNORECASE)


def _move_pin(helpers: Any, path: Path, pattern: re.Pattern[str], pin: str) -> str:
    text = helpers.read_text(path)
    if "labconstrictor_tools" not in text:
        return "has no Tools bridge hook: nothing to move"
    lines = text.splitlines(keepends=True)
    hits = []
    for index, line in enumerate(lines):
        match = pattern.match(line.rstrip("\r\n"))
        if match:
            hits.append((index, match))
    if not hits:
        return "has no LC_TOOLS_PIN line (unpinned source or its own Tools source): left as it is"
    if len(hits) > 1:
        return f"has {len(hits)} LC_TOOLS_PIN lines: left as it is, set the pin by hand to {pin}"
    index, match = hits[0]
    current = match.group(2)
    if current == pin:
        return f"already pins Tools {pin}: unchanged"
    if current != OLD_PIN:
        return f"has its own pin {current}: left as it is (the template pin is now {pin})"
    ending = lines[index][len(lines[index].rstrip("\r\n")) :]
    lines[index] = f"{match.group(1)}{pin}{match.group(3)}{ending}"
    helpers.write_text(path, "".join(lines))
    return f"updated: Tools pin {OLD_PIN} -> {pin}"


# --------------------------------------------------------------------------------------------------------------------------------
# 2. Pinned actions
# --------------------------------------------------------------------------------------------------------------------------------
def _unpinned_uses(text: str) -> list[str]:
    """`uses:` lines of third-party actions that are not pinned by SHA (local `./` actions and `docker://` need no pin)."""
    found = []
    for line in text.replace("\r\n", "\n").split("\n"):
        match = ANY_USES.match(line)
        if match and not re.fullmatch(r"[0-9a-f]{40}", match.group(2)) and not match.group(1).startswith(("./", "docker:")):
            found.append(line.strip())
    return found


def _migrate_workflow(helpers: Any, repo_root: Path, relative: Path) -> str:
    path = repo_root / relative
    if not path.is_file():
        return "not present in this repository (nothing was created)"
    new = _resource_text(helpers, relative)
    current = helpers.read_text(path)
    current_lf = current.replace("\r\n", "\n")
    if current_lf == new:
        return "already the pinned template file: unchanged"
    if current_lf == _unpin(new):
        newline = helpers.detect_newline(current)
        helpers.write_text(path, new.replace("\n", newline))
        return "updated: every third-party action is pinned by commit SHA"
    left = _unpinned_uses(current)
    if not left:
        return "customised and already pinned: left as it is"
    shown = "; ".join(left[:6]) + ("; ..." if len(left) > 6 else "")
    return f"SKIPPED: customised, so it was left unchanged ({len(left)} third-party action(s) not pinned by SHA: {shown}). Pin them by hand, see {DOCS_URL}"


# --------------------------------------------------------------------------------------------------------------------------------
# 3. Install guide
# --------------------------------------------------------------------------------------------------------------------------------
def _section(text: str, heading: str) -> str:
    """The section of `heading` in the (LF) resource text, up to the next `## ` heading, with its trailing blank line."""
    match = re.search(rf"^{re.escape(heading)}\n.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"section {heading!r} was not found in the template resource")
    return match.group(0)


def _migrate_install_doc(helpers: Any, repo_root: Path) -> str:
    path = repo_root / INSTALL_DOC
    if not path.is_file():
        return "not present in this repository (nothing was created)"
    resource = _resource_text(helpers, INSTALL_DOC)
    current = helpers.read_text(path)
    newline = helpers.detect_newline(current)
    lf = current.replace("\r\n", "\n")
    done = []
    for heading, anchor in ((INSTALL_BEFORE_HEADING, INSTALL_BEFORE_ANCHOR), (INSTALL_UPDATE_HEADING, INSTALL_UPDATE_ANCHOR)):
        if re.search(rf"^{re.escape(heading)}\s*$", lf, re.MULTILINE):
            continue
        position = re.search(rf"^{re.escape(anchor)}\s*$", lf, re.MULTILINE)
        if not position:
            return f"SKIPPED: no line {anchor!r} to insert {heading!r} before; add the sections by hand from {DOCS_URL}"
        lf = lf[: position.start()] + _section(resource, heading) + lf[position.start() :]
        done.append(heading[3:])
    if not done:
        return "already has the install rules: unchanged"
    helpers.write_text(path, lf.replace("\n", newline))
    return "updated: added " + " and ".join(repr(d) for d in done)


# --------------------------------------------------------------------------------------------------------------------------------
# 4. Tools guide
# --------------------------------------------------------------------------------------------------------------------------------
def _migrate_tools_doc(helpers: Any, repo_root: Path, replacements: dict[str, str], pin: str) -> str:
    destination = repo_root / TOOLS_DOC
    if not destination.is_file():
        return "not present in this repository (nothing was created)"
    current = helpers.read_text(destination)
    newline = helpers.detect_newline(current)
    new = helpers.render_template(_resource_text(helpers, TOOLS_DOC), replacements, newline)
    if current == new:
        return "unchanged"
    old = helpers.render_template(_resource_text(helpers, TOOLS_DOC).replace(pin, OLD_PIN), replacements, newline)
    if current != old:
        return "SKIPPED: not the 0.1.17 text (customised), so it was left unchanged; it names the pinned Tools tag " + pin
    helpers.write_text(destination, new)
    return "updated: written"


def migrate(repo_root: Path, context: dict[str, Any]) -> None:
    """Move the template Tools pin, pin the workflow actions, add the install rules (idempotent, surgical, never raises for a customised file)."""
    _ = context
    helpers = _load_helpers()
    pin = new_pin(helpers)
    try:
        replacements = helpers.load_replacements(repo_root)
    except (OSError, ValueError) as exc:
        log(f"could not read the app name from construct.yaml ({exc}): the guides are written without app names.")
        replacements = {}

    changed = 0

    def report(name: Path, step: Any) -> None:
        nonlocal changed
        try:
            status = step()
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            status = f"SKIPPED: {exc}; left unchanged. See {DOCS_URL}"
        if status.startswith("updated"):
            changed += 1
        log(f"{name}: {status}")

    for relative, pattern in ((POST_INSTALL_SH, SH_PIN_LINE), (POST_INSTALL_BAT, BAT_PIN_LINE)):
        if not (repo_root / relative).is_file():
            log(f"{relative}: SKIPPED, file not found in this repository (nothing was created).")
            continue
        report(relative, lambda relative=relative, pattern=pattern: _move_pin(helpers, repo_root / relative, pattern, pin))
    for relative in WORKFLOWS:
        report(relative, lambda relative=relative: _migrate_workflow(helpers, repo_root, relative))
    report(INSTALL_DOC, lambda: _migrate_install_doc(helpers, repo_root))
    report(TOOLS_DOC, lambda: _migrate_tools_doc(helpers, repo_root, replacements, pin))

    if changed:
        log(f"done: {changed} file(s) changed. Review the pull request before merging; the pin reaches users with the next release of the app.")
    else:
        log("done: no repository changes were required.")
