# Template 0.1.17: install Tools before the package import check

Design note for the 0.1.17 migration (`.template_sync/migrations/v0_1_16_to_v0_1_17.py`). It changes only the installer scripts `app/bash_bat_scripts/post_install.sh` and `post_install.bat` of an app repository. How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md) (a new installer is needed; nothing edits an existing install).

## 1. The problem

Template 0.1.16 ran `import <package>` (the check that the installed app package works) **before** the block that installs `labconstrictor-tools` and registers the app. An app package that imports `labconstrictor_tools` at module level therefore failed with `ModuleNotFoundError` and the installer aborted (Linux/macOS `exit 1`; Windows `ERROR: Installed ... package could not be imported`, exit code 2). Seen in a clean-sandbox test of the Playground 0.0.2 release; Playground fixed its own package with lazy imports. An app whose only importer is `<package>_lc_tools` (NucleiSky) was never affected, because that module is not imported by the check.

## 2. The change

New order in `post_install` (both systems):

1. install the app package (`pip install --no-deps --no-build-isolation`),
2. if the package ships `<package>_lc_tools`: install `labconstrictor-tools` (the pinned tag, or `LC_TOOLS_SPEC`),
3. `import <package>` check (unchanged),
4. register the app with `labconstrictor_tools register` (unchanged, as before after the check).

A failed Tools install is a `WARNING` in `menuinst_debug.log`, the registration is skipped, and the installation goes on. If the package itself needs Tools at import time, the import check then fails, which is the correct outcome. Apps without a `<package>_lc_tools` module do not install Tools at all, as before.

* `post_install.sh`: the pin (`LC_TOOLS_PIN`), `LC_TOOLS_MODULE` and the `pip install` move into a block between the package install and the import check, which sets `LC_TOOLS_READY=1` on success; the registration block keeps its place and registers only when `LC_TOOLS_READY` is 1.
* `post_install.bat`: the pin, `LC_TOOLS_SPEC` and the `pip install` (still through Python, so `cmd.exe` never re-parses the value) move into a subroutine `:install_lc_tools` at the end of the file, called with `CALL` before the import check. A subroutine is used because `%VAR%` inside a parenthesised block is expanded when the block is read, so a variable set in that block could not be used in it. The registration block keeps its place and registers only when `LC_TOOLS_READY` is 1. The file keeps CRLF line endings.

## 3. What the migration does

Surgical and idempotent, like the 0.1.16 migration. For each of the two scripts it recognises the 0.1.16 hook (the template text, an unpinned hand-integrated hook, or a hook with another Tools source) and only

* inserts the Tools install block before the import check line,
* moves the lines that define the pin / module / spec out of the registration block into that block (a one-line comment stays behind),
* replaces the single `pip install` line of the registration block by the `LC_TOOLS_READY` check.

The Tools source of the app (default URL or its own `LC_TOOLS_SPEC` default) is copied, not replaced. Not touched: any other line, the app's own customisations, files without the hook (the 0.1.16 migration adds the hook first when the chain runs both), scripts that do not match the known shape (printed as `SKIPPED` with the manual step), and line endings. A script that already contains `LC_TOOLS_READY` is left unchanged, so a second run changes nothing. Nothing is deleted.

If the package name cannot be told, the scripts are still migrated from the names found in the hook itself (the tools module name is read from the existing hook), so no package detection is needed.

## 4. What is not verified here

* The Windows script is not run by the template tests (no `cmd.exe`); the end-to-end check is the smoke workflow of LabConstrictor-Tools (`smoke_migration.yml`) on a Windows runner.
* Installed copies are not changed: a new installer must be built and run.
