# Template 0.1.21: no administrator prompt when uninstalling on Windows

Design note for the 0.1.21 migration (`.template_sync/migrations/v0_1_20_to_v0_1_21.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

On Windows, uninstalling any app made with template 0.1.20 or earlier shows a User Account Control prompt for `python.exe` from an unknown publisher. The command line is `"<app folder>\python.exe" -m conda.core.initialize "<app folder>\tmp\tmp….json"`. Whether the user answers **Yes** or **No**, the step fails and a "Failed to clean AutoRun" error with Abort, Retry and Ignore follows; **Retry** shows the prompt again. With **Ignore** the app is removed and nothing outside the app folder is changed. **Abort**, the default button, stops the uninstall halfway and leaves the app folder on disk. Found in round alpha.4 (LabConstrictor-Tools issue 141, row WIN-15) with Playground, GuessTheCondition, NucleiSky and VLab4Mic.

Why it happens:

1. Constructor's NSIS installer installs the packages with its bundled `_conda.exe` (conda-standalone) and sets `CONDA_SAFETY_CHECKS=disabled`. Before conda 26.9.3, disabled safety checks skip the step that fills `paths_data` in each package record (`conda-meta/*.json`): every package without prefix placeholders gets `"paths": []`, `conda-launchers` included. Our installers were built with conda-standalone 26.5.2.
2. The app environment includes `conda` (26.9.3 in the alpha.4 installers). Since 26.9.0, conda finds the Windows launcher stub (`share/conda-launchers/cli-64.exe`) through the `paths_data` of `conda-launchers`. With an empty list it raises `FileNotFoundError`, although the file is on disk.
3. Because the environment has `conda`, the uninstaller runs `condabin\conda.bat init cmd.exe --reverse --user`, even with `initialize_conda: false`. `conda init` treats any `OSError` as a permission problem (`needs sudo  …\Scripts\conda.exe`) and reruns itself as administrator. As administrator the file is still not found, so the prompt never helps.

Upstream: [conda/conda#16856](https://github.com/conda/conda/issues/16856), fixed by [conda/conda#16855](https://github.com/conda/conda/pull/16855) in conda 26.9.3. Miniforge hit the same bug ([conda-forge/miniforge#913](https://github.com/conda-forge/miniforge/issues/913)); the fix there is to build with conda-standalone 26.9.3 or later.

## 2. What changes

| Part | Change |
|---|---|
| `.tools/bash/create_constructor_environment.sh` | The constructor environment is created with `"conda-standalone>=26.9.3"`. Constructor itself only requires `conda-standalone >=24.11.0`, so without the pin the solver may pick an older one. The installer's `_conda.exe` then writes complete `paths_data`, and `conda init --reverse` finds the launcher. |

## 3. What the migration does

* The known 0.1.20 `conda create` line is replaced by the pinned line and a comment. The line endings of the file are kept.
* A file that already has the 0.1.21 line is `unchanged`. A file that names `conda-standalone` in another way, or where the 0.1.20 line is not found once (customised), is `SKIPPED`: add `"conda-standalone>=26.9.3"` to its `conda create` by hand.
* A file that is not in the repository is not created.

## 4. Adopting it

Take this template version (the synchronization pull request), then build and release a new installer. Installed copies do not change: an app installed with an older installer keeps the prompt when it is uninstalled. Answering **No** and then **Ignore** is safe; see [Troubleshooting an installed app](troubleshooting_installed_app.md).

## 5. What is not verified here

* The installer build and uninstall are not run by the template tests. They check the migration on the 0.1.20 script, with LF and CRLF line endings, for an app that already has the pin and for a customised file, and that the migrated script is valid shell.
* That a build with conda-standalone 26.9.3 or later writes complete `paths_data` comes from the upstream fix and the Miniforge report. It has not yet been checked on a LabConstrictor installer: after the next Windows build, `conda-meta\conda-launchers-*.json` should list six paths, and the uninstall should show no prompt.
