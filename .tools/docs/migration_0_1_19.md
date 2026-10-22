# Template 0.1.19: src_change.yaml in every installer, Python series in setup.py

Design note for the 0.1.19 migration (`.template_sync/migrations/v0_1_18_to_v0_1_19.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. What changes

| Part | Problem | Change |
|---|---|---|
| `.tools/python/bump_constructor.py` | `ensure_extra_files` removed the `.tools/meta/src_change.yaml` mapping from `extra_files` and then re-added it only if it was not in `existing_sources`, a list made before the removal. An app whose `construct.yaml` had the mapping lost it at the next release, and got it back at the one after: every other installer had no `src_change.yaml`, so the Welcome notebook of that release could not offer source-code updates. Found in CellTracksColab 1.1.4. | The mapping is always re-added after the removal. |
| `.tools/python/merge_requirements.py` | It wrote the exact Python release of the installer into `setup.py` (`python_requires=">=3.12.13"`). A source install (`pip install -e .`) then failed on any earlier patch release of the same series, for example the Python 3.12.3 of Ubuntu 24.04: `current Python version (3.12.3) does not satisfy Python>=3.12.13`. | It writes the series (`python_requires=">=3.12"`). `environment.yaml` keeps the exact pin used by the installer. |
| `setup.py` of an app | Holds the exact release written by the old script. | Changed to the series by the migration (only that exact shape). |

The installers are not affected by the `setup.py` change: they bundle their own Python, which already satisfied the old requirement.

## 2. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file. Each file gets one line in the output: `updated`, `unchanged` or `SKIPPED` with the reason.

* **`bump_constructor.py` and `merge_requirements.py`.** The known 0.1.18 block is replaced by the 0.1.19 block. A file that already has the 0.1.19 block is `unchanged` (CellTracksColab took both fixes before this version, in its pull requests 66 and 67). A file where the 0.1.18 block is not found once (customised) is `SKIPPED`; apply the change of section 1 by hand.
* **`setup.py`.** A `python_requires=">=X.Y.Z"` (single or double quotes) becomes `">=X.Y"`. The template placeholder `">=PYTHON_VERSION"`, a series that is already there, or any other specifier (for example `~=3.12.1`) is `unchanged`. Two or more `python_requires` lines: `SKIPPED`.
* A file that is not in the repository is not created.

## 3. Adopting it

Take this template version (the synchronization pull request), then build and release a new installer: the release workflow runs the new `bump_constructor.py`, which puts `src_change.yaml` back into `construct.yaml` and into the installer. Installed copies do not change: reinstall.

## 4. What is not verified here

* The installer build itself is not run by the template tests. The tests run the new `bump_constructor.py` three times on a small app (`src_change.yaml` stays mapped every time; the 0.1.18 script drops and restores it) and `merge_requirements.py` on a small app (it writes `>=3.12` and keeps `python=3.12.13` in `environment.yaml`).
