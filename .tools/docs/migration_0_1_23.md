# Template 0.1.23: no template placeholder in the installer

Design note for the 0.1.23 migration (`.template_sync/migrations/v0_1_22_to_v0_1_23.py`), issue [#40](https://github.com/CellMigrationLab/LabConstrictor/issues/40). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

The template's files hold placeholders (`PROJECT_NAME`, `PYTHON_PROJ_NAME`, ...) that the repository initialisation, the [LabConstrictor form](https://labconstrictor-form.streamlit.app) (`CellMigrationLab/LabConstrictor_streamlit`), replaces with the app's names. It replaces each placeholder only in the files it lists for it, and three files were missing from those lists:

| File | Placeholder left | Effect |
|---|---|---|
| `app/bash_bat_scripts/post_install.sh` and `.bat` | `PYTHON_PROJ_NAME` (since template 0.1.16) | An app with Python code in `src/` cannot be installed: the last step runs `import PYTHON_PROJ_NAME` and fails with `No module named 'PYTHON_PROJ_NAME'`. Found with StarDist2D 1.0.0. |
| `app/python_scripts/launch_jupyter.py` | `PROJECT_NAME` | The launcher's error messages say "PROJECT_NAME could not start". |
| `.tools/templates/Welcome_template.ipynb` | `PROJECT_NAME` | The Welcome notebook says "Welcome to PROJECT_NAME!" (LabConstrictor Playground). |

Apps that reached 0.1.16 through the migrations are not affected by the first row: the 0.1.16 migration wrote the package name. Nothing caught it, because the workflows never install the installers they build.

## 2. What changes

| Part | Change |
|---|---|
| The form (`LabConstrictor_streamlit`) | The three files are added to its placeholder lists. Its test initialises the template's current `main` and fails when any placeholder is left, so a placeholder added to the template later is caught too. |
| `.tools/python/check_placeholders.py` (new) | Fails when an initialisation placeholder is left in a file the installer ships (`app/**`, `construct.yaml`, `setup.py`, `environment.yaml`), and names the file, the line and the fix. It also refuses the raw, uninitialised template. Placeholders filled in later on purpose are not checked: `BASE_PATH_KEYWORD` (at install), `PYTHON_VERSION` and `JUPYTERLAB_VERSION` (by the requirements workflow). |
| `.github/workflows/release_constructor.yml` | Runs the check in both jobs, right after `bump_Welcome_notebook.py`: before the version commit and before any installer is built. |

The check fails the release rather than fixing the files itself: the maintainer sees what was wrong, fixes the repository once, and publishes the release again.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **Placeholders.** In `post_install.sh`, `post_install.bat`, `launch_jupyter.py` and `Welcome_template.ipynb`, a placeholder that is still there is replaced: `PYTHON_PROJ_NAME` with the app's Python package, `PROJECT_NAME` with the app name. A file without placeholders is `unchanged`.
  * The package is found as in the 0.1.16 migration: the single `<package>_lc_tools` module in `src/`, else the single package in `src/`, else the name in `setup.py`, else the `[project]` name of `pyproject.toml`. When none is found, the file is `SKIPPED`: replace the placeholder by hand.
  * The app name is the `menu_name` of `app/menuinst/notebook_launcher.json`, which the form wrote, else `PROJECT_DISPLAY_NAME` in `launch_jupyter.py`.
* **The check.** `.tools/python/check_placeholders.py` is created. A repository with its own file of that name keeps it (`SKIPPED`).
* **The workflow.** The check is added after the `bump_Welcome_notebook.py` command in each job of `release_constructor.yml`. A workflow without that command (customised) is `SKIPPED`: add the five lines by hand (see the template's file).
* An uninitialised repository (`construct.yaml` still names `UNDERSCORED_PROJECT_NAME`) is not touched.

## 4. Adopting it

Take this template version (the synchronization pull request) and release a new installer. If the release stops at "check_placeholders.py", its log lists each file and line: replace the placeholder there, commit, and publish the release again. Installed copies do not change: reinstall.

## 5. What is checked here, and what is not

* Tests (`tests/test_template_sync_0_1_23.py`): the check on clean and broken apps; the migration on a broken 0.1.22 app (then the check passes and a second run changes nothing), on a healthy app, with CRLF, an unknown package, a customised workflow and the raw template; the sync chain from 0.1.22; the live workflow equals the 0.1.22 workflow migrated.
* The check was run after the release scripts (`bump_version.py`, `bump_constructor.py`, `bump_Welcome_notebook.py`) on copies of NucleiSky, LabConstrictor Playground, Guess the Condition, LabConstrictor_Demo, LabChronicle, CellTracksColab, StarDist2D, CellPatcher and VLab4Mic. It passes for all of them except the Playground, whose Welcome notebook really says "Welcome to PROJECT_NAME!": the migration repairs it.
* The installers themselves are not built or installed by these tests.
