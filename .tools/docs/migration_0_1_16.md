# Template 0.1.16: how the Tools bridge hooks reach an existing app

Design note for the 0.1.16 migration (`.template_sync/migrations/v0_1_15_to_v0_1_16.py`). Short version: the hooks reach an **existing app** through the normal template synchronization pull request, and reach **people who already installed it** only when they install a newer installer of the app. Nothing in the template can change an installed copy by itself.

## 1. What "update" means in this template (checked in the code)

There are two different things called "the app":

| | Where it lives | How it changes |
|---|---|---|
| The **app repository** (created from the template) | GitHub | The weekly workflow `sync_template.yml` ("Sync with Template Repository") compares `.template_sync/manifest.yaml` (`template_version`) of the repository with the template's `main`, copies the template's `.template_sync` folder, runs the chain of migrations with `.template_sync/sync.py`, and opens a pull request ("Sync template to version X"). It needs the secret `LABCONSTRICTOR_SYNC_TOKEN`; without it the workflow stops with an error and the repository stays on its version. The owner reviews and merges. |
| The **installed app** | The user's computer (a conda prefix made by the `constructor` installer) | Never by the template. `post_install` runs once while an installer runs. Nothing runs on update: there is no self-update step, no version check in the scripts, and the notebook update check (`notebook_latest_versions.yaml`) only tells people that a notebook has a newer version. |

So the real path of a template change to a user is: template `main` (version bump) -> sync pull request in the app repository (migration edits the scripts) -> owner merges -> owner publishes a **release** of the app (`release_constructor.yml` builds the installers from the repository) -> the user downloads and runs the new installer.

What the installer does with the scripts (from `construct.yaml` and the `constructor` sources):

* `post_install.sh/.bat` are run by the installer at the end of every install (`pkgs/post_install.*`). On Linux and macOS `bash installer.sh -u -p <prefix>` updates an existing prefix and runs `post_install` again; without `-u` the installer refuses an existing folder. On Windows the `.exe` can be run again on the same folder (not verified, see below).
* `pre_uninstall.bat` is copied by the Windows installer to `<prefix>\pre_uninstall.bat` and run by the uninstaller (constructor's `pre_uninstall` exists on Windows only).
* `pre_uninstall.sh` and `uninstall.sh` are plain `extra_files` copied to the prefix on Linux and macOS (constructor has no uninstall hook there). `post_install` fills the `BASE_PATH` token with the real prefix.

## 2. What the migration changes

In the **app repository**, in this order (each file independently):

| File | Change |
|---|---|
| `app/bash_bat_scripts/post_install.sh` | the hook block (detect `<package>_lc_tools`, `pip install` of Tools, `labconstrictor_tools register`) is inserted before the `include_path.py` line |
| `app/bash_bat_scripts/post_install.bat` | the same block for Windows; `SETLOCAL EnableExtensions` becomes `SETLOCAL EnableExtensions DisableDelayedExpansion` |
| `app/bash_bat_scripts/pre_uninstall.sh` / `.bat` | the `unregister` call (with a warning if a registry entry stays) is inserted before the `menuinst ... remove` line |
| `app/bash_bat_scripts/uninstall.sh` | only if it is exactly the 0.1.15 text: a failed `pre_uninstall` and a failed `rm -rf` are reported (exit 1 if the folder cannot be removed) |
| `.tools/docs/tools_bridge.md`, `.tools/docs/README.md` | the guide and its index entry |

`construct.yaml` needs no change: `pre_uninstall.sh`, `uninstall.sh` and the post/pre scripts are already listed, and `bump_constructor.py` adds every file under `src/` (including `src/<package>_lc_tools/`) at release time. The tool module itself (`src/<package>_lc_tools/`) belongs to the app author and is not created by the migration.

Rules:

* **Idempotent.** A script that already mentions `labconstrictor_tools` is left unchanged; a second run changes nothing (tested). Apps that carried the hooks before (the `bridge-test` apps) are therefore untouched.
* **Surgical.** The block is inserted before a known line, so the app's own edits stay. If the script is missing, was rewritten, or lacks the variables the block uses (`PYTHON_EXE`, `PROJECT_ROOT`, `LOG_FILE`, `BASE_PATH`), that file is **skipped with a message** (`SKIPPED: ...`) and the rest still runs. The migration never raises for such a file, so the sync pull request is still created.
* **No tools, no effect.** For an app without a `<package>_lc_tools` module the hooks are inert: `post_install` finds no module and skips the step; `pre_uninstall` stays silent unless a registry entry exists. The migration says so in its log.
* **Never deletes.** It writes only the files in the table (no `.orig`, nothing removed); notebooks, `src/`, requirements, `construct.yaml` and `labconstrictor-app.yaml` are not touched. Line endings of each file are kept.
* **Logs.** Every step prints one line prefixed `[migration 0.1.16]` in the "Run template migrations" step of the workflow.
* **Version.** `template_version` goes to 0.1.16 (the template's rule: bump when users must act; a sync pull request is only opened when the version is higher).
* **Not pinned yet.** The inserted block installs Tools from `.../archive/refs/heads/main.zip` exactly as in the template 0.1.15 scripts (`LC_TOOLS_SPEC` overrides it). Pinning to a tag (`refs/tags/v0.2.0-rc.1.zip`, tag created by the maintainer later) is a separate change of that one string in the template scripts and in this migration's resources.

## 3. What cannot be migrated (honest answer)

* **A copy that is already installed cannot be changed by a template version.** Its `post_install` already ran; the Linux/macOS `pre_uninstall.sh`/`uninstall.sh` and the Windows `pre_uninstall.bat` in the prefix are old files. They change only when a newer installer is run over the prefix (`-u`, or the `.exe` again) or after an uninstall and a fresh install. There is no mechanism in the template, and none is added here, that edits files inside someone's prefix: it would need code that runs on the user's computer without the user installing anything.
* **An app only gets tools if a release contains `src/<package>_lc_tools/`.** The tool module is a file of the installer (`extra_files`); an installed app whose installer did not ship it has nothing to register, whatever the scripts say. So "apps pick up the hooks when they update" means: the app owner merges the sync pull request **and publishes a new release**, and users install it.
* **Old installs keep uninstalling the old way.** Uninstalling an app installed from an old installer does not unregister anything (it never registered). That is harmless. The reverse case is the risk: an app registered by a new installer and then removed by deleting its folder by hand leaves an entry in `~/.labconstrictor/apps` (see `labconstrictor-tools doctor`).
* **Repositories that did not receive the sync** (no `LABCONSTRICTOR_SYNC_TOKEN`, workflow disabled, sync pull request not merged) stay on their version and do not get the hooks; they can copy the files by hand from `.tools/docs/tools_bridge.md`.
* **Customised scripts** are skipped (see above): those apps need the block added by hand.
* **Windows `.bat`.** The migration and the generated `.bat` text are tested in the template tests on the files only. Running them on Windows is verified only by the smoke workflow in LabConstrictor-Tools, not here.

## 4. Test plan

* Template tests (`tests/test_template_sync_0_1_16.py`): old scripts of 0.1.15 become byte-identical to the 0.1.16 template scripts rendered for the app; second run changes nothing; hooks already present are untouched; CRLF/LF preserved; customised and missing files skipped without failing; user files untouched; the `sync.py` entry point; the migrated bash scripts run against a stub Python (register, failed registration, no tools module, uninstall unregisters and removes only the prefix, failed unregister only warns).
* LabConstrictor-Tools workflow `smoke_migration.yml`: an app at an old template version is installed, migrated by this branch, a new installer is built and installed over it, `labconstrictor-tools list` and `doctor` are checked, then the app is uninstalled, on Linux, macOS and Windows.
