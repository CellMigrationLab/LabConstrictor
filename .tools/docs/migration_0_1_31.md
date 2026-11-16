# Template 0.1.31: no silent change of a notebook's package versions, no lost work when a notebook is updated

Design note for the 0.1.31 migration (`.template_sync/migrations/v0_1_30_to_v0_1_31.py`), issues [#48](https://github.com/CellMigrationLab/LabConstrictor/issues/48) and [#49](https://github.com/CellMigrationLab/LabConstrictor/issues/49). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problems

**#48, the requirements merge changed versions without a word.** `merge_requirements.py` (run by **Updates on notebook change**) merged the `requirements.yaml` of every notebook and, for a package required by several notebooks, kept the highest version: the policy of issue #4 ("if two versions are in conflict in principle take the newest one"). For scientific workflows a successful install does not mean the same results, so a notebook validated with `numpy==1.26.4` silently ran with `numpy==2.0.0`. Running it showed more than the code review that found it (all exited with 0):

| Notebook A | Notebook B | Merged until 0.1.30 |
|---|---|---|
| `numpy==1.26.4` | `numpy==2.0.0` | `numpy==2.0.0`, in either file order |
| `numpy<2.0` | | `numpy==2.0`: every requirement was written as `==`, here the one excluded version |
| `numpy<2` | `numpy>=2.1` | `numpy==2.1` |
| `numpy==1.26.4 ; sys_platform == "win32"` | `numpy==2.0.0 ; sys_platform != "win32"` | only the second line: no numpy on Windows |

NucleiSky's notebooks pin `cellpose`, `ipywidgets`, `scikit-image`, `tifffile`, `torch` and `zarr` to different versions, and LabChronicle's pin `tqdm` to two versions: they relied on this. The old merge also treated `scikit-image` and `scikit_image` as two packages (pip then refuses the file), and wrote `ipywidgets==>=7.0.0` when no notebook gave a Python version.

**#49, the notebook update could overwrite the user's work.** The **Update** button of the Welcome notebook downloaded the new notebook and wrote it over the user's copy, with their code changes, parameters and saved outputs, with no question and no copy. A failed write could leave a broken notebook, and a private repository without a token crashed the button.

## 2. What changes

| Part | Change |
|---|---|
| `.tools/python/merge_requirements.py` | Requirements are kept as written and combined per package (`numpy>=1.24,<2`); names are compared as pip compares them. Different exact pins, a pin outside another notebook's range, or ranges no version meets stop the merge, before any file is written, with every notebook and requirement (sorted, so the file order cannot hide one). `requirements_overrides.yaml` can decide explicitly, with a required reason; each decision is written at the top of the generated files. Requirements with different markers stay separate lines. A notebook's OS-specific requirements are checked against the common ones. `--check` only looks for conflicts. |
| `.tools/requirements.txt` | `packaging==25.0` (versions and specifiers as pip reads them). |
| `requirements_overrides.yaml` (new, only where needed) | See section 3. |
| `.github/workflows/update_on_notebook_change.yml` | A push of `requirements_overrides.yaml` runs the workflow and the merge. |
| `.github/workflows/release_constructor.yml` | The bump-version job runs `merge_requirements.py --check` after `check_placeholders.py`: a release stops while a conflict is unresolved (a failed merge leaves the previous `requirements.txt` in place, which would otherwise be released). |
| `.tools/templates/Welcome_template.ipynb` | **Update** asks first, says where the copy goes and to close the notebook's tab; then downloads, checks that the download is a notebook, copies the current file to `<notebook>.backup-<date>.ipynb` (never overwriting an earlier backup), writes the new notebook to a temporary file and moves it into place, and only then records the new version. Cancel or any failure changes nothing. The app-version check that decides whether a notebook can be updated is unchanged. |

Why not detect local changes: JupyterLab saves outputs into the notebook (and autosaves), so a used notebook always differs from the installed one; a check would ask every time anyway. Asking every time and always keeping a copy is simpler and loses nothing.

Why a range check of our own: a lock failure is only a warning (the installer then installs the plain `requirements.txt`), so an impossible range would reach the users. `satisfiable()` tries every version a requirement names and versions just above it; a range only a closer version could meet is reported as a conflict (stop and decide), never guessed.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`merge_requirements.py`** is replaced by the 0.1.31 file when it is still the 0.1.30 template file; a customised one is left as it is (`SKIPPED`).
* **`.tools/requirements.txt`** gets `packaging==25.0` unless it installs packaging already.
* **`requirements_overrides.yaml`** is created only when the notebooks' `dependencies` already pin a package to different versions. Each entry keeps the version the merge chose until now (the newest pin), so the app installs what it installed before, and its reason says so and lists the pins: check each one and replace the reason with yours. An existing file is left as it is.
* **`update_on_notebook_change.yml`:** three known lines (push paths, changed files, the merge condition); a customised workflow is `SKIPPED` (run the workflow by hand after changing the overrides).
* **`release_constructor.yml`:** the check goes after the first `check_placeholders.py` command (the bump-version job), only when the repository's `merge_requirements.py` knows `--check`.
* **`Welcome_template.ipynb`:** the update handler of the notebook table is replaced (compared line by line, trailing spaces ignored) and the backup function added; a customised table cell is `SKIPPED`. The Welcome notebook of the next release is made from it.

## 4. Adopting it

Take this template version (the synchronization pull request). If it created `requirements_overrides.yaml`, check each decision with the notebooks that pin another version; change the notebooks or the decision as needed. Then release a new installer: users get the safe update with it.

## 5. What is checked here, and what is not

* Tests (`tests/test_template_sync_0_1_31.py`): the merge on the cases of #48 (both file orders, ranges, markers, names, OS-specific lists, overrides with and without a reason, `--check` writes nothing); the backup function (first install, backup, two updates in the same second, a download that is not a notebook); the migration on 0.1.30 files and on customised ones, the seeded overrides of a NucleiSky-like app and the merge accepting them, CRLF, a second run; the sync chain from 0.1.30.
* The migration and the merge were run on copies of the real apps.
* The confirmation dialog and the buttons of the Welcome notebook are not run by these tests: they need a person in an installed app.
