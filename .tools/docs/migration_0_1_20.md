# Template 0.1.20: lock files, no lost workflow pushes, a launcher that starts fresh

Design note for the 0.1.20 migration (`.template_sync/migrations/v0_1_19_to_v0_1_20.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. What changes

| Part | Problem | Change |
|---|---|---|
| `update_on_notebook_change.yml`, `update_on_src_change.yaml` | One push that changes both `src/` and `notebooks/` starts both workflows. They shared one concurrency group, so they ran one after the other, but each checks out the commit that triggered it: the second one committed on top of an old `main` and its push was rejected (`non-fast-forward`). Seen in CellMigrationLab/LabChronicle runs 41727822989 (notebook workflow) and 41800906840 (src workflow). The notebook workflow then ran "Revert user commit that broke requirements" (its condition was any failure), created a revert of the user's merge commit, and was stopped only because that push was rejected too. | The commit step commits, and when the push is rejected it rebases onto the latest branch (`git rebase --autostash`) and pushes again (5 attempts). The revert runs only when the conda test failed, on top of the latest branch, with `-m 1` only for a merge commit. Each workflow has its own concurrency group (a group keeps only one waiting run, so a third push cancelled the waiting run of the other workflow). The checkout stays on the triggering commit, because `update_changelog.py` and `update_version_last_commit.py` compare it with its parent. `stefanzweifel/git-auto-commit-action` is no longer used. |
| Requirements (`requirements*.txt`) | The installer ran `pip install -r requirements.txt`: the notebooks' packages are pinned, the packages they depend on are not, so two installations of one release could get different versions. | `.tools/python/lock_requirements.py` (run by the notebook workflow after the merge) writes `requirements*.lock.txt` next to each requirements file with `uv pip compile --universal`: every package with its exact version, for Windows, macOS and Linux. `post_install.sh` / `.bat` install the lock file when the installer bundles one (`bump_constructor.py` bundles it), and the conda test of the workflow installs it too, then runs `pip check` (a warning only). |
| `launch_jupyter.py` | When JupyterLab stopped, the terminal window closed at once (macOS, Linux) or stayed open with a prompt (Windows). Every app shares `~/.jupyter/lab/workspaces` and opens JupyterLab in the home folder, so a new session restored the notebooks of other apps (a NucleiSky notebook in a LabChronicle session). | The launcher asks to press Enter when JupyterLab stops (also after an error; not for `--self-test`, `--print-ca-bundle` or `--no-wait`). JupyterLab gets a new, empty workspace folder at every launch, removed when it stops: only the Welcome notebook opens. Settings and themes are kept (they are not in the workspaces). |
| `notebook_launcher.json` | On Windows, menuinst runs the shortcut with `cmd /K`, which keeps the window open after the command. | The Windows command ends with `& exit`, so the window closes after Enter. |
| `notebook_usage.md` | Said to stop JupyterLab with `Ctrl+C`. | Names **File > Shut Down** first, and the Enter prompt. |

### How a lock file is made

* One lock file per requirements file: `requirements.lock.txt`, `requirements_gpu.lock.txt`, `requirements-windows.lock.txt`, ... A package that only one platform needs carries an environment marker (`colorama==0.4.6 ; sys_platform == 'win32'`).
* `--python-version` is the Python of `environment.yaml`. uv reads it as the lowest Python, so a few packages can appear twice with a `python_full_version` marker; pip installs the line that matches the installer's Python.
* The conda packages of `environment.yaml` (`jupyterlab`, `pip`, `setuptools`, `certifi`, ...) are installed by the installer itself: they are not written to the lock file (their dependencies are), and a conda pin such as `jupyterlab=4.4.0` constrains the resolution.
* The per-OS files are resolved with `requirements.lock.txt` as constraints, so a package both files need gets one version. The GPU file is resolved on its own (its PyTorch comes from the CUDA index, whose `--extra-index-url` line is copied to the lock file).
* Versions only, no hashes.
* The header holds a fingerprint of the inputs (the requirement lines, the Python and JupyterLab versions, the lock format). The file is written again only when one of them changes, so a release without new requirements installs the same versions as the previous one. To move every package to its newest version, delete the lock files and run **Updates on notebook change** by hand.
* If a file cannot be locked (no solution, uv missing), the step prints a GitHub warning, removes the out-of-date lock file and goes on: the installer installs the plain requirements file. `bump_constructor.py` removes the mapping of a lock file that is gone, so the installer build does not fail on it.

## 2. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file. Each file gets one line in the output: `updated`, `unchanged` or `SKIPPED` with the reason.

* **The two workflows, `test_conda_environment.sh`, `launch_jupyter.py`.** Replaced by the 0.1.20 file only when the app's file is still the 0.1.19 template file (rendered with the app's name; line endings ignored). A customised file is `SKIPPED`: apply the change of section 1 by hand.
* **`lock_requirements.py`.** Created (it is new). An app that has its own file keeps it (`SKIPPED`).
* **`.tools/requirements.txt`.** `uv==0.13.3` is added, unless the file already names `uv`.
* **`post_install.sh` / `.bat`.** The known install lines are replaced by the lines that pick the lock file. If one of them is not found exactly once, the file is `SKIPPED`.
* **`bump_constructor.py`.** `ensure_lock_files_in_extra_files` is inserted before `def ensure_extra_files(` and called after `ensure_requirements_in_extra_files(data)`. Both lines must be found once (LabChronicle's own script qualifies).
* **`notebook_launcher.json`.** The Windows command is added (the shared command plus `"&", "exit"`) when the file has the template shape and formatting; a file with its own Windows command is `SKIPPED`.
* **`notebook_usage.md`.** The sentence on stopping JupyterLab is replaced when it is the 0.1.19 text.
* A file that is not in the repository is not created (except `lock_requirements.py`, when `.tools/python` exists).

## 3. Adopting it

1. Merge the synchronization pull request.
2. Run **Actions > Updates on notebook change > Run workflow** once: it writes the lock files (the next push of a `requirements.yaml` would too). Check that the run is green and committed `requirements*.lock.txt`.
3. Build and release a new installer: it bundles the lock files and the new launcher. Installed copies do not change: reinstall.

## 4. Limitations and what is not verified here

* **macOS terminal.** After Enter, Terminal.app closes the window only if its profile says so (*Settings > Profiles > Shell > When the shell exits*); otherwise it shows `[Process completed]`. Not tested on a Mac yet.
* **Windows and `Ctrl+C`.** Stopping JupyterLab with `Ctrl+C` makes `cmd` ask `Terminate batch job (Y/N)?` after Enter: `N` closes the window, `Y` leaves it open. **File > Shut Down** avoids the question.
* **The lock covers pip only.** Constructor already fixes the conda packages when the installer is built.
* **Tested here:** the commit and revert steps of the workflows run with bash and git against a local origin that moved during the run (a rebased push, a conflict that pushes nothing, the revert of a merge and of a plain commit); `lock_requirements.py` with a fake uv (fingerprint, constraints, index lines, failures); `bump_constructor.py`; the launcher's workspace folder and Enter prompt; the migration on a 0.1.19 app and on customised files. `uv pip compile --universal` itself was tried by hand on LabChronicle's requirements (CPU, GPU with the CUDA index, Windows file). Not tested: a real GitHub Actions run, an installer build, and a launch on Windows, macOS and Linux.
