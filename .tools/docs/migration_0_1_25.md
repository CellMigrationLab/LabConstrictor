# Template 0.1.25: publish the app's Python code on PyPI at each release (opt-in)

Design note for the 0.1.25 migration (`.template_sync/migrations/v0_1_24_to_v0_1_25.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md); this one changes no installed app: it only adds a release step that a developer turns on.

## 1. The problem

An app's own Python code (`src/<package>`) was installed into the app and could be imported by its notebooks, but nothing in the template published it on PyPI: only NucleiSky did, with a workflow of its own. The package itself was not ready for PyPI either:

| Part | What was wrong |
|---|---|
| `setup.py` | `install_requires=[]`: the dependencies lived in `requirements.txt` (and its lock file) only. No description (README). |
| `bump_version.py` | It never wrote the release version into `setup.py`, which kept the version of the initialisation (`0.0.1`). |
| The release | The tag points to the commit *before* the "Update version" commit of the release workflow, so a job that builds from the tag cannot trust the committed version. |

## 2. Design (chosen 2026-11-12)

| Question | Choice | Why |
|---|---|---|
| On or off | A new workflow in every app, **off by default**: both jobs have `if: vars.PYPI_PUBLISH == 'true' \|\| vars.PYPI_PUBLISH == 'testpypi'`. | An app that does not use it sees skipped jobs, never a failure. A repository *variable* is the switch because a secret cannot be read in a job's `if:`. |
| When | A published GitHub release, the moment the installers are built. | One version for the installers and for PyPI. |
| Version | The tag without the `v`, as `release_constructor.yml` does. `pypi_package.py` writes it into `setup.py` of the checkout (not committed). | The tagged commit has the previous version. |
| Authentication | PyPI trusted publishing (OIDC): `permissions: id-token: write`, GitHub environment `pypi`, `pypa/gh-action-pypi-publish` pinned by SHA. No secret, no API-token fallback. | Recommended by PyPI. A project-scoped token needs the project to exist already; a pending publisher creates it at the first release. |
| Trial | `PYPI_PUBLISH=testpypi` uploads to TestPyPI (same environment name, a publisher registered on test.pypi.org). | A dry run that does not use the PyPI name. |
| Name | `name=` of `setup.py`. `distribution.pip` of `labconstrictor-app.yaml` is **not** the switch; when present, it must be the same name (PEP 503 normalised), otherwise the build stops. | The App Centre tells people to `pip install` the `distribution.pip` name. Renaming silently could publish the wrong code under it: VLab4Mic's `src/` holds only `vlab4mic_lc_tools` (`setup.py` name `vlab4mic-lc-tools`), while a `distribution.pip: vlab4mic` would name VLab4Mic itself, which is published from another repository. |
| Dependencies | `setup.py` reads `requirements.txt` when the package is built: one requirement per line, as written (exact pins included). Options, paths and URLs are left out (`pypi_package.py` warns about each). | One list for the installer and PyPI. The installer builds the package with `pip install --no-deps --no-build-isolation`, and `requirements.txt` is next to `setup.py` there: a line setuptools would refuse is dropped, so it can never break an installation. `MANIFEST.in` puts `requirements.txt` in the source distribution, so a wheel built from it has the same dependencies. |
| Description | `README.md` (Markdown), and the repository as the `Source` link (from `GITHUB_REPOSITORY`, set by GitHub Actions). | Both files may be missing (the installer): the package still builds. |

Two jobs, as PyPI recommends: `build` (no special permission) runs `.tools/python/pypi_package.py` and stores `dist/` as an artifact; `publish` (only `id-token: write`, environment `pypi`) downloads it and uploads it.

`pypi_package.py` stops **before building**, with a GitHub error annotation, when:

* there is no package in `src/` (a folder with an `__init__.py`);
* the version is not X.Y.Z;
* the index already has that version (`/pypi/<name>/<version>/json` answers 200); when the index cannot be asked, it only warns (the upload then fails if the version exists);
* another workflow of the repository uploads to PyPI (`pypa/gh-action-pypi-publish` or `twine upload`): the release would be uploaded twice;
* `distribution.pip` and `setup.py` name different packages;
* `setup.py` still has `PYTHON_PROJ_NAME` or `PYTHON_VERSION`;
* `pyproject.toml` describes the package (a `[project]` table) with another version than the release (its version is not rewritten).

After `python -m build` (the wheel is built from the source distribution), it checks the name and version of both files, refuses a dependency given as a URL (PyPI refuses it on upload), and checks that the wheel has the dependencies of the source distribution.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`.tools/python/pypi_package.py`** is created; a repository with its own file of that name keeps it (`SKIPPED`).
* **`.github/workflows/publish_pypi.yml`** is created, off. It is **not** created when another workflow of the repository already uploads to PyPI (NucleiSky's `publish_to_pypi.yml`, which publishes when `project.version` of `pyproject.toml` changes on `main`): the log says so, and that nothing is needed to keep publishing that way. To move to the template's workflow, delete yours, copy `publish_pypi.yml` from the template, and register it on pypi.org (a project you own: **Manage** > **Publishing**).
* **`setup.py`** is replaced by the 0.1.25 template's, with the app's name, version and Python series, only when it is exactly the template's earlier file with those three values filled in (CellTracksColab, LabChronicle, LabConstrictor_Demo, Stardist2D). A `setup.py` changed by hand (the Playground and GuessTheCondition list their dependencies, CellPatcher has a URL dependency, VLab4Mic names one package, NucleiSky is a shim for `pyproject.toml`) is left as it is (`SKIPPED`); if such an app turns PyPI publishing on, its `setup.py` is built as it is, and `pypi_package.py` reports what PyPI would refuse.
* **`MANIFEST.in`** is created only next to the 0.1.25 `setup.py`. An app's own `MANIFEST.in` is kept; without the line `include requirements.txt`, the log asks to add it.
* **`bump_version.py`:** three known blocks (the `setup.py` path and pattern, the new `bump_setup_py()`, its call in `main()`). Customised, `SKIPPED`: the release then leaves `setup.py`'s version alone (`publish_pypi.yml` still publishes the release version).

## 4. Adopting it

Take this template version (the synchronization pull request). Nothing is published until the one-time setup in [Upload external code](external_code_upload.md#4-publish-the-code-on-pypi-optional): a pending trusted publisher on pypi.org (owner, repository, workflow `publish_pypi.yml`, environment `pypi`), then the repository variable `PYPI_PUBLISH=true`. To turn it off, delete the variable. Failures are described in [Troubleshooting](troubleshooting.md#publishing-to-pypi-fails).

## 5. What is checked here, and what is not

* Tests (`tests/test_template_sync_0_1_25.py`): the workflow is off without the variable, uses trusted publishing, no secret, actions pinned by SHA; `setup.py` keeps the placeholders the form, `bump_constructor.py`, `merge_requirements.py` and `check_placeholders.py` rely on; what `setup.py` passes to setuptools with and without `requirements.txt` and `README.md` (the installer), also without `packaging`; every stop of `pypi_package.py`; **the source distribution and the wheel of an initialised copy are built** (without network) and their metadata checked; `bump_version.py` writes the release version into `setup.py` and keeps CRLF; the migration on 0.1.24 files (a second run changes nothing), with CRLF, the uninitialised template, customised files, NucleiSky's own workflow and missing folders; the sync chain from 0.1.24.
* The migration was also run on copies of real apps (NucleiSky, the Playground, Stardist2D, CellPatcher, VLab4Mic, CellTracksColab, LabChronicle, LabConstrictor_Demo, GuessTheCondition), with the whole chain from their template versions (0.1.19 to 0.1.22), then a second time (no change), and the package of each app that got the workflow was built with `pypi_package.py` (no upload). CellTracksColab, LabChronicle, LabConstrictor_Demo and Stardist2D got the new `setup.py`; the others kept theirs. Every build passed except CellPatcher's, which stops as intended: its `setup.py` needs two packages from GitHub URLs, which PyPI refuses.
* **Nothing was uploaded** to PyPI or TestPyPI: the `publish` job (trusted publishing, `pypa/gh-action-pypi-publish`) and the `if:` on `vars` are checked only by reading them. The first real check is a release of an app with `PYPI_PUBLISH=testpypi`.
