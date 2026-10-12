"""Template 0.1.15 -> 0.1.16: add the LabConstrictor Tools bridge hooks to an app repository.

What this changes (in the app's *repository*, through the template sync pull request; an installed copy of the app is
only ever changed by installing a newer installer, see .tools/docs/migration_0_1_16.md):

* app/bash_bat_scripts/post_install.sh / .bat   register the app with the Tools bridge after install
* app/bash_bat_scripts/pre_uninstall.sh / .bat  unregister it on uninstall
* app/bash_bat_scripts/uninstall.sh             report a failed pre-uninstall or a failed removal
* .tools/docs/tools_bridge.md and its entry in .tools/docs/README.md

Rules this migration keeps:

* It edits surgically: a block is inserted before a known line of the app's own script, so changes the app made to its scripts
  stay. A script that already has the hook (it mentions labconstrictor_tools) is left unchanged, so running it twice, or on an
  app that carried the hooks before (bridge-test apps), changes nothing.
* A script that is missing or too different to edit safely is skipped with a message that says what to do by hand. The
  migration never raises for that reason: the sync pull request must still be created.
* Nothing is deleted. Only the files listed above are written; notebooks, src/, requirements, construct.yaml and
  labconstrictor-app.yaml are not touched. Line endings of each file are kept.
* The hooks are inert for an app without a <package>_lc_tools module (post_install finds no module and skips the step;
  pre_uninstall only warns when a registry entry exists), so the migration is applied to every app.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable


RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "resources" / "v0_1_15_to_v0_1_16"
SCRIPTS = Path("app/bash_bat_scripts")
POST_INSTALL_SH = SCRIPTS / "post_install.sh"
POST_INSTALL_BAT = SCRIPTS / "post_install.bat"
PRE_UNINSTALL_SH = SCRIPTS / "pre_uninstall.sh"
PRE_UNINSTALL_BAT = SCRIPTS / "pre_uninstall.bat"
UNINSTALL_SH = SCRIPTS / "uninstall.sh"
TOOLS_DOC = Path(".tools/docs/tools_bridge.md")
DOCS_INDEX = Path(".tools/docs/README.md")

# Resource files: copies of the template files of 0.1.16 (a test checks they stay identical to the template).
# Scripts are used as the source of the hook blocks; the doc is copied.
MANAGED_FILES = (POST_INSTALL_SH, POST_INSTALL_BAT, PRE_UNINSTALL_SH, PRE_UNINSTALL_BAT, UNINSTALL_SH, TOOLS_DOC)

INDEX_ENTRY = "- [Expose tools to Napari and Fiji (experimental)](tools_bridge.md)"
HOOK_MARKER = "labconstrictor_tools"
TAG = "[migration 0.1.16]"

# uninstall.sh of template 0.1.15 and the replacement of 0.1.16 (exact text only: a changed uninstall.sh is left alone).
OLD_UNINSTALL = 'if [ -f "$PREFIX/pre_uninstall.sh" ]; then\n    bash "$PREFIX/pre_uninstall.sh"\nfi\nrm -rf "$PREFIX"\n'
NEW_UNINSTALL = (
    'if [ -f "$PREFIX/pre_uninstall.sh" ]; then\n'
    "    # best effort: shortcut/registry cleanup must not stop the removal, but a failure must be visible\n"
    '    if ! bash "$PREFIX/pre_uninstall.sh"; then\n'
    '        echo "WARNING: pre-uninstall cleanup failed (see the messages above); shortcuts or the tools registry entry may remain." >&2\n'
    "    fi\n"
    "fi\n"
    'if ! rm -rf -- "$PREFIX"; then\n'
    '    echo "ERROR: could not remove $PREFIX; PROJECT_NAME is only partly uninstalled. Close anything using it and delete that folder manually." >&2\n'
    "    exit 1\n"
    "fi\n"
)


def log(message: str) -> None:
    print(f"{TAG} {message}")


def _load_helpers():
    """Reuse the rendering helpers of the 0.1.10 migration (token replacement, newline detection, file IO)."""
    path = Path(__file__).resolve().parent / "v0_1_9_to_v0_1_10.py"
    spec = importlib.util.spec_from_file_location("template_sync_helpers_0_1_16", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resource_lines(helpers: Any, relative: Path, replacements: dict[str, str]) -> list[str]:
    source = RESOURCE_ROOT / relative
    if not source.is_file():
        raise FileNotFoundError(f"Template resource not found: {source}")
    return helpers.render_template(helpers.read_text(source), replacements, "\n").split("\n")


def _find(lines: list[str], predicate: Callable[[str], bool], start: int = 0) -> int | None:
    for index in range(start, len(lines)):
        if predicate(lines[index]):
            return index
    return None


def _block(resource: list[str], starts: Callable[[str], bool], ends: Callable[[str], bool], lead: int = 0) -> list[str]:
    """Lines of the resource from the line where `starts` is true (minus `lead` lines before it) up to, not including, the line where `ends` is true."""
    first = _find(resource, starts)
    last = _find(resource, ends, (first or 0) + 1) if first is not None else None
    if first is None or last is None:
        raise ValueError("the hook block was not found in the template resource")
    return resource[first - lead : last]


def _insert_before(helpers: Any, path: Path, block: list[str], anchor: Callable[[str], bool], required: list[str]) -> str:
    """Insert `block` before the first line of the file at `path` for which `anchor` is true. Returns a status text."""
    text = helpers.read_text(path)
    if HOOK_MARKER in text:
        return "already has the Tools bridge hook: unchanged"
    missing = [item for item in required if item not in text]
    if missing:
        return f"SKIPPED: the script does not define {', '.join(missing)}, so the hook cannot be added safely; add it by hand from .tools/docs/tools_bridge.md"
    newline = helpers.detect_newline(text)
    lines = text.splitlines(keepends=True)
    index = _find(lines, anchor)
    if index is None:
        return "SKIPPED: the line the hook goes before was not found (the script was customised); add the hook by hand from .tools/docs/tools_bridge.md"
    if lines[index - 1 : index] and not lines[index - 1].endswith(("\n", "\r")):
        lines[index - 1] += newline
    lines[index:index] = [line + newline for line in block]
    helpers.write_text(path, "".join(lines))
    return "hook added"


def _migrate_post_install_sh(helpers: Any, repo_root: Path, resource: list[str]) -> str:
    block = _block(resource, lambda l: l.startswith("# --- Optional: expose the app's tools"), lambda l: "include_path.py" in l and "notebook_launcher.json" in l, lead=1)
    return _insert_before(
        helpers, repo_root / POST_INSTALL_SH, block,
        lambda l: "include_path.py" in l and "notebook_launcher.json" in l,
        ['PYTHON_EXE="', 'PROJECT_ROOT="', 'LOG_FILE="'],
    )


def _migrate_post_install_bat(helpers: Any, repo_root: Path, resource: list[str]) -> str:
    path = repo_root / POST_INSTALL_BAT
    block = _block(resource, lambda l: l.startswith("REM Optional: expose the app's tools"), lambda l: "include_path.py" in l and "notebook_launcher.json" in l)
    status = _insert_before(
        helpers, path, block,
        lambda l: "include_path.py" in l and "notebook_launcher.json" in l,
        ['SET "PYTHON_EXE=', 'SET "PROJECT_ROOT=', 'SET "LOG_FILE='],
    )
    if status == "hook added":
        # The hook reads LC_TOOLS_SPEC and the version into variables: keep a "!" in a value from being re-interpreted.
        text = helpers.read_text(path)
        old, new = "SETLOCAL EnableExtensions", "SETLOCAL EnableExtensions DisableDelayedExpansion"
        newline = helpers.detect_newline(text)
        lines = text.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.strip().upper() == old.upper():
                lines[index] = new + (newline if line.endswith(("\n", "\r")) else "")
                helpers.write_text(path, "".join(lines))
                status += " (SETLOCAL now DisableDelayedExpansion)"
                break
    return status


def _migrate_pre_uninstall(helpers: Any, repo_root: Path, resource: list[str], relative: Path, starts: Callable[[str], bool]) -> str:
    block = _block(resource, starts, lambda l: "menuinst.api import remove" in l)
    return _insert_before(
        helpers, repo_root / relative, block,
        lambda l: "menuinst.api import remove" in l,
        ["BASE_PATH"] if relative.suffix == ".sh" else [],
    )


def _migrate_uninstall_sh(helpers: Any, repo_root: Path, replacements: dict[str, str]) -> str:
    path = repo_root / UNINSTALL_SH
    text = helpers.read_text(path)
    newline = helpers.detect_newline(text)
    normalised = text.replace("\r\n", "\n")
    new = helpers.render_template(NEW_UNINSTALL, replacements, "\n")
    if new in normalised:
        return "already up to date: unchanged"
    if OLD_UNINSTALL not in normalised:
        return "SKIPPED: uninstall.sh differs from the template of 0.1.15 (customised); left unchanged. Optional: see .tools/docs/migration_0_1_16.md"
    helpers.write_text(path, normalised.replace(OLD_UNINSTALL, new, 1).replace("\n", newline))
    return "updated (pre-uninstall failures and a failed removal are reported)"


def _migrate_docs(helpers: Any, repo_root: Path, replacements: dict[str, str]) -> list[str]:
    results = []
    source = RESOURCE_ROOT / TOOLS_DOC
    destination = repo_root / TOOLS_DOC
    rendered = helpers.render_template(helpers.read_text(source), replacements, helpers.detect_newline(helpers.read_text(destination)) if destination.exists() else "\n")
    if destination.exists() and helpers.read_text(destination) == rendered:
        results.append(f"{TOOLS_DOC}: unchanged")
    else:
        helpers.write_text(destination, rendered)
        results.append(f"{TOOLS_DOC}: written")

    index_path = repo_root / DOCS_INDEX
    if not index_path.is_file():
        results.append(f"{DOCS_INDEX}: not present, index entry skipped")
        return results
    text = helpers.read_text(index_path)
    if "tools_bridge.md" in text:
        results.append(f"{DOCS_INDEX}: entry already present, unchanged")
        return results
    entry = INDEX_ENTRY
    newline = helpers.detect_newline(text)
    lines = text.splitlines(keepends=True)
    anchor = _find(lines, lambda l: "external_code_upload.md" in l)
    if entry is None or anchor is None:
        results.append(f"{DOCS_INDEX}: SKIPPED (no place for the entry; the page is still reachable as tools_bridge.md)")
        return results
    if not lines[anchor].endswith(("\n", "\r")):
        lines[anchor] += newline
    lines.insert(anchor + 1, entry + newline)
    helpers.write_text(index_path, "".join(lines))
    results.append(f"{DOCS_INDEX}: entry added")
    return results


def has_tools_module(repo_root: Path) -> bool:
    src = repo_root / "src"
    if not src.is_dir():
        return False
    return any(src.glob("*_lc_tools/__init__.py")) or any(src.glob("*_lc_tools.py"))


def migrate(repo_root: Path, context: dict[str, Any]) -> None:
    """Add the Tools bridge hooks to the installer scripts of the repository (idempotent, never deletes, never raises for a customised file)."""
    _ = context
    helpers = _load_helpers()
    try:
        replacements = helpers.load_replacements(repo_root)
    except (OSError, ValueError) as exc:
        log(f"SKIPPED: could not read the app name from construct.yaml ({exc}); nothing was changed.")
        return

    log("app has a <package>_lc_tools module: the hooks will register it." if has_tools_module(repo_root)
        else "app has no <package>_lc_tools module: the hooks are added but stay inert until you add one (see .tools/docs/tools_bridge.md).")

    steps: list[tuple[Path, Callable[[], str]]] = []
    resources = {path: _resource_lines(helpers, path, replacements) for path in (POST_INSTALL_SH, POST_INSTALL_BAT, PRE_UNINSTALL_SH, PRE_UNINSTALL_BAT)}
    steps.append((POST_INSTALL_SH, lambda: _migrate_post_install_sh(helpers, repo_root, resources[POST_INSTALL_SH])))
    steps.append((POST_INSTALL_BAT, lambda: _migrate_post_install_bat(helpers, repo_root, resources[POST_INSTALL_BAT])))
    steps.append((PRE_UNINSTALL_SH, lambda: _migrate_pre_uninstall(helpers, repo_root, resources[PRE_UNINSTALL_SH], PRE_UNINSTALL_SH, lambda l: l.startswith("# best effort: a failure must not stop"))))
    steps.append((PRE_UNINSTALL_BAT, lambda: _migrate_pre_uninstall(helpers, repo_root, resources[PRE_UNINSTALL_BAT], PRE_UNINSTALL_BAT, lambda l: "labconstrictor_tools unregister" in l)))
    steps.append((UNINSTALL_SH, lambda: _migrate_uninstall_sh(helpers, repo_root, replacements)))

    changed = 0
    for relative, step in steps:
        if not (repo_root / relative).is_file():
            log(f"{relative}: SKIPPED, file not found in this repository (nothing was created).")
            continue
        try:
            status = step()
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            status = f"SKIPPED: {exc}"
        if status.startswith(("hook added", "updated")):
            changed += 1
        log(f"{relative}: {status}")

    try:
        for line in _migrate_docs(helpers, repo_root, replacements):
            if line.endswith(("written", "entry added")):
                changed += 1
            log(line)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        log(f"docs SKIPPED: {exc}")

    if changed:
        log(f"done: {changed} file(s) changed. Review the pull request before merging; the tools register after a NEW installer of the app is installed.")
    else:
        log("done: no repository changes were required.")
