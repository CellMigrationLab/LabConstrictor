# Template 0.1.24: download links for "v" tags, installers only for the supported systems, the app's own Jupyter kernel

Design note for the 0.1.24 migration (`.template_sync/migrations/v0_1_23_to_v0_1_24.py`), issues [#41](https://github.com/CellMigrationLab/LabConstrictor/issues/41), [#42](https://github.com/CellMigrationLab/LabConstrictor/issues/42) and [#43](https://github.com/CellMigrationLab/LabConstrictor/issues/43). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problems

| Issue | What happened | Seen in |
|---|---|---|
| #41 | A release tagged `v1.0.0` wrote download links to `/releases/download/1.0.0/...`. The release workflow strips the `v` for the version, and `bump_version.py` used that version for the folder of the link too. The real folder is the tag, `v1.0.0`, so every button of the download page returned 404. | StarDist2D 1.0.0 |
| #42 | Every release built the four installers (Windows, Linux, Macs with Apple silicon and with Intel), also for a system the app cannot run on. TensorFlow 2.17 and later has no wheels for Intel Macs, so that installer failed at its last step. The release page and the download page still offered it. | StarDist2D 1.0.0 |
| #43 | Jupyter looks for kernels in the user's folder before the app's own folder. On a computer where someone once ran `python -m ipykernel install --user`, the user's "python3" kernel won, the notebook ran in that other Python, and its first import of the app failed with `No module named '<app>'`. For the app's prefix, a constructor base environment, jupyter_core (5.x) does not prefer the environment by itself. | StarDist2D 1.0.0 on Linux |

## 2. What changes

| Part | Change |
|---|---|
| `.github/workflows/release_constructor.yml` | Both "Determine release version" steps also export the tag as typed, `RELEASE_TAG`. A new `platforms` job runs `release_platforms.py`, and the build job takes its matrix from it (`fromJSON(needs.platforms.outputs.matrix)`). |
| `.tools/python/release_platforms.py` (new) | Reads `distribution.platforms` of `labconstrictor-app.yaml` and writes the build matrix: only the systems listed, all four without the key (or without the file), as before. It fails, with the reason, when the file is not valid YAML, when `platforms` is not a list, or when it lists none of the four (`windows-arm64` and `linux-arm64` have no build). |
| `.tools/python/bump_version.py` | The download links point to the tag (`--tag`, default `$RELEASE_TAG`, else the version); the installer names keep the bare version. It refuses a tag that is neither the version nor `v` + the version. A system that is not built gets a note on the download page instead of its button. A later release also finds links written for a `v` tag. |
| `app/python_scripts/launch_jupyter.py` | `run_jupyter()` sets `JUPYTER_PREFER_ENV_PATH=1` before JupyterLab is imported: the app's own kernel (and configuration) comes before the user's. It is set, not defaulted, so a user's `JUPYTER_PREFER_ENV_PATH=0` cannot bring the problem back. JupyterLab settings and themes are not affected: they are not on these paths. |

`bump_version.py` reads the tag from the environment, so it and the workflow do not depend on each other: an app whose `bump_version.py` is customised and was left unchanged keeps working, with the old links.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`release_platforms.py`** is created. A repository with its own file of that name keeps it (`SKIPPED`).
* **`bump_version.py`:** seven known blocks are changed (the import of `os`, `replace_version_placeholder` and two new functions, the download-page function, the `--tag` option and its check, the call). When one of them is not found exactly once, the file is customised and is left as it is (`SKIPPED`); apply the change by hand from the template's file. A change elsewhere in the file (CellPatcher refuses pre-release versions in `main()`) does not stop it.
* **`release_constructor.yml`**, two independent parts:
  * the `RELEASE_TAG` line before each `RAW="${RAW#v}"` line;
  * the `platforms` job and the matrix, only when the build job's matrix is exactly the template's four builds. A matrix changed by hand (the LabConstrictor Playground removed the Intel Mac build) is left as it is (`SKIPPED`). To move to `distribution.platforms`, list the systems in `labconstrictor-app.yaml` and copy the `platforms` job and the `matrix:` line from the template's workflow.
* **`launch_jupyter.py`:** the variable goes before the comment and the import of `jupyterlab.labapp` in `run_jupyter()`; without them, `SKIPPED`.

## 4. Adopting it

Take this template version (the synchronization pull request). If your app cannot run on a system, leave that system out of `distribution.platforms` in `labconstrictor-app.yaml` (see [App Centre manifest](app_manifest.md)); the App Centre already uses the same list. Then release a new installer: users get the kernel fix by installing it. A release whose `platforms` job fails is described in [Troubleshooting](troubleshooting.md).

## 5. What is checked here, and what is not

* Tests (`tests/test_template_sync_0_1_24.py`): the download links for `v1.2.3` and `1.2.3` tags, the tag check, the notes for systems that are not built; the matrix with and without `distribution.platforms` and the failures; the launcher sets the variable before it imports JupyterLab, also over a user's `0`; the migration on 0.1.23 files (the result is the live template file, a second run changes nothing), with CRLF, a customised `bump_version.py` (also CellPatcher's), a customised matrix and missing files; the sync chain from 0.1.23.
* jupyter_core's own handling of `JUPYTER_PREFER_ENV_PATH` was checked by hand by the issue's author on the StarDist2D Linux install, not by these tests.
* A release with the new workflow has not run yet: the `platforms` job and `fromJSON` matrix are checked only by reading them.
