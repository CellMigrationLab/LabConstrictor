# Template 0.1.18: new Tools pin, pinned GitHub Actions, install rules

Design note for the 0.1.18 migration (`.template_sync/migrations/v0_1_17_to_v0_1_18.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. What changes

| Part | Change |
|---|---|
| Tools pin | `LC_TOOLS_PIN` in `app/bash_bat_scripts/post_install.sh` and `post_install.bat` moves from `v0.2.0-rc.1` to `v0.3.0-alpha.1`. |
| GitHub Actions | Every third-party `uses:` in the workflows is pinned by the commit SHA of the tag it named (the tag stays as a trailing comment). No version is upgraded. |
| Install guide | `.tools/docs/install.md` states three install rules (section 4). |
| Tools guide | `.tools/docs/tools_bridge.md` names the new pinned tag. |
| App hosts | The installer bundles the app's `labconstrictor-app.yaml` and `post_install` passes it to `labconstrictor-tools register --app-manifest`, so the `hosts:` line of the app decides which hosts list it (section 7). |
| Template CI | Only in the template repository itself: the workflow `.github/workflows/tests.yml` runs the template's tests, `black`, `ruff` and `mypy`. It does not run in apps (it checks `github.repository`) and is not delivered by the migration. |

The pinned tag `v0.3.0-alpha.1` of LabConstrictor-Tools must exist before an installer built from this template is used: the installer downloads the archive of that tag.

## 2. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file. Each file gets one line in the output: `updated`, `unchanged` or `SKIPPED` with the reason.

* **Pin.** In each of the two scripts the line `LC_TOOLS_PIN="v0.2.0-rc.1"` (`SET "LC_TOOLS_PIN=v0.2.0-rc.1"` in the `.bat`) is changed to the new tag **only if it still holds exactly the old template value**. An app with its own pin, an unpinned hook (the source is `refs/heads/main.zip` or its own `LC_TOOLS_SPEC`) or no hook stays as it is and a note says so. Only the value inside the quotes changes.
* **Workflows.** Five files: `check_app_manifest.yml`, `release_constructor.yml`, `sync_template.yml`, `update_on_notebook_change.yml`, `update_on_src_change.yaml`. A file is replaced by the pinned template file **only if it is still identical to the previous template version** (line endings are ignored when comparing). A file that is already the pinned template file is unchanged. A file that the app customised (or pinned in part) is skipped, and the message lists the third-party actions that are still pinned by tag only, so the maintainer can pin them by hand with the table in section 3. A workflow that is not in the repository is not created.
* **Install guide.** If `.tools/docs/install.md` exists, the sections "Before you install" and "Update an installed app" are inserted before `## Install on Windows` and before `## Next` (each only if its heading is missing); if an anchor line is missing the step is skipped with a message.
* **Tools guide.** `.tools/docs/tools_bridge.md` is rewritten only if it is still the 0.1.17 text.
* **App hosts.** See section 7.

Changing files under `.github/workflows/` needs the synchronization token to have the `workflows=write` permission, as for every earlier workflow change ([template_synchronization.md](template_synchronization.md)).

## 3. Pinned actions

| Action | Tag | Commit SHA |
|---|---|---|
| actions/checkout | v4 | `11d5960a326750d5838078e36cf38b85af677262` |
| actions/setup-python | v4 | `7f4fc3e22c37d6ff65e88745f38bd3157c663f7c` |
| actions/upload-artifact | v7 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| tj-actions/changed-files | v44 | `2d756ea4c53f7f6b397767d8723b3a10a9f35bf2` |
| conda-incubator/setup-miniconda | v3 | `fc2d68f6413eb2d87b895e92f8584b5b94a10167` |
| stefanzweifel/git-auto-commit-action | v5 | `b863ae1933cb653a53c021fe36dbb774e1fb9403` |
| softprops/action-gh-release | v2 | `3bb12739c298aeb8a4eeaf626c5b8d85266b0e65` |
| peter-evans/create-pull-request | v6 | `c5a7806660adbe173f04e3e038b0ccdcd758773c` |

Mutable tags can be moved to other code (the March 2025 `tj-actions/changed-files` incident), and these workflows hold write tokens. The SHAs are the ones apps already carry after their own pinning pull requests (for example NucleiSky pull request 37). To move to a newer version, change the SHA and the tag comment together, in the live workflow and in the copy under `.template_sync/resources/` of the latest migration.

## 4. The three install rules

Stated in `.tools/docs/install.md` with this wording (a test checks that every doc that states them uses the same sentences):

* The install path must contain no space: the installer refuses a path with a space. Use a path such as `C:\LabConstrictor\<app>` on Windows or `~/labconstrictor/<app>` on macOS and Linux.
* On macOS and Windows, update an app by uninstalling the old version first and then installing the new one: the installer does not install over an existing install.
* On Linux, running the installer with `-u` updates in place only if the previous install finished; otherwise delete `<prefix>/pkgs` or uninstall the app and install it again.

## 5. Template tests in CI

`.github/workflows/tests.yml` runs on every pull request and on every push to `main`, with read-only permissions: all `tests/test_*.py`, then `black --check`, `ruff check` and `mypy` on `.template_sync`, `.tools/python` and `tests`. The linters are configured in `pyproject.toml` to the state of the code at 0.1.18 (no behaviour change was made to satisfy them); tighten the configuration when code is cleaned up.

## 6. What is not verified here

* Installed copies are not changed: a new installer must be built and run.
* The Windows script is not run by the template tests; the end-to-end check is `smoke_migration.yml` of LabConstrictor-Tools on a Windows runner.

## 7. App hosts: the installer passes the `hosts:` line to Tools

Problem found by the Tools readiness check: Tools lists an app in a host (Napari, Fiji, QuPath) only for the hosts its registry entry names, but the installer never told Tools. `labconstrictor-app.yaml` was not in the installer and `post_install` called `register` without `--app-manifest`, so every registered app had no `hosts` and every host listed it.

What the template does now:

* **Bundle.** `bump_constructor.py` adds `labconstrictor-app.yaml: <project folder>/labconstrictor-app.yaml` to `extra_files` in `construct.yaml` when the file exists in the repository (a mapping to a missing file would fail the installer build, so it is not added otherwise; an existing mapping whose file is gone is reported, not removed).
* **Register.** In `post_install.sh` / `.bat` the Tools hook passes `--app-manifest <install folder>/labconstrictor-app.yaml` to `register`. If the file is not in the installation, the app is registered without hosts and `menuinst_debug.log` says so with the sentence Tools uses: `'<app>' declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose`. A manifest that is there but has no `hosts:` line is read by Tools, which registers the app without hosts and prints the same sentence (it reaches the same log); the hook does not parse the file itself. There is no silent fallback; a manifest with an invalid `hosts:` line makes `register` refuse (Tools exit code 2), which the hook logs as `WARNING: tool registration failed`.

What the migration does in an app repository (same rules as above: surgical, idempotent, never deletes, never raises, line endings kept):

* `construct.yaml`: adds the `extra_files` entry **only if** the repository has a `labconstrictor-app.yaml` and the entry is not there yet, with the project folder read from the `Welcome.ipynb` entry. No manifest: `SKIPPED` with the instruction (add the file, then the entry). An `extra_files` that is not a block list, or no readable project folder: `SKIPPED`.
* `post_install.sh` / `.bat`: inserts the manifest lookup and the log lines in the Tools hook and adds the argument to the app's own `register` line (the app's own arguments stay). A hook that already has `--app-manifest` or `--hosts` is unchanged. A hook of another shape (no `lc_note` before the register line in the `.sh`; a register line that is not `IF NOT ERRORLEVEL 1 ... >> LOG 2>&1` in the `.bat`) is `SKIPPED` and nothing is written.
* `bump_constructor.py` of an app is not touched: the entry the migration writes into `construct.yaml` survives it. An app that adds its manifest later adds the mapping by hand (or takes the new `bump_constructor.py` of the template).

Adopting it, per app: have a `labconstrictor-app.yaml` with a `hosts:` line at the repository root, take this template version (the synchronization pull request), build and release a new installer. Installed copies do not change: reinstall.

The template CI runs the live `post_install` in a fake prefix on Linux, macOS and Windows (`tests/smoke/post_install_hosts.py`) with the real `labconstrictor-tools` and checks that the registry entry's `hosts` equals the `hosts:` line of each real manifest in `tests/fixtures/manifests`. Until the Tools tag exists the job installs Tools from the main branch of LabConstrictor-Tools (`LC_TOOLS_SPEC` in `.github/workflows/tests.yml`, the one place to change; delete it once the tag exists).
