# Template 0.1.37: the user guides, checked and rewritten

Design note for the 0.1.37 migration (`.template_sync/migrations/v0_1_36_to_v0_1_37.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

The website imports the template's guides into three tracks (use an app, build an app, connect an app). A review against the template, the repository form and the installer found:

* wrong advice: `workflow_status.md` said to test a big change on a branch first, but the workflows run only on pushes to `main` (and by hand); `notebook_upload.md` asked to "run the bottom cell" so that `requirements.yaml` matches the new notebook version, a cell that does not exist;
* missing facts a reader needs: the form accepts only `package==version` dependencies and only a classic `ghp_` token; every notebook of an app must use the same `python_version`; the generator saves `<notebook>_requirements.yaml`;
* the guides a first-time reader follows to the end (install, initialise, requirements, upload, installers) did not say what you need, how to check that it worked and what to do if it does not; the website checks for these sections;
* `template_synchronization.md` linked the wrong previous and next pages; `tools_bridge.md`, the first page of the "Connect an app" track, began with what the page covers and kept a paragraph for template maintainers;
* history, design-note links and implementation detail in pages written for app users.

Some of these pages could not change before: older migrations install them as frozen copies, and their tests compared the live page with those copies.

## 2. What changes

Seventeen guides in `.tools/docs/` are replaced (the list is `FILES` in the migration): `accept_pull_request.md`, `app_manifest.md`, `before_getting_started.md`, `create_repository.md`, `executable_creation.md`, `external_code_upload.md`, `initialise_repository.md`, `install.md`, `installer_images.md`, `notebook_requirements.md`, `notebook_upload.md`, `notebook_usage.md`, `template_synchronization.md`, `tools_bridge.md`, `troubleshooting.md`, `troubleshooting_installed_app.md` and `workflow_status.md`.

Headings and anchors that other pages or the website link to are kept, in particular the system sections of `install.md` ("Install on Windows", "Install on a Mac", "Install on Linux"), which the website shows on each app page. `install.md` renames "Before you install" to "Before you start". No code changes.

## 3. What the migration does

* Each guide is replaced by the 0.1.37 page when it is still the 0.1.36 template file, compared with LF line endings (the frozen copies are in `.template_sync/resources/v0_1_36_to_v0_1_37/previous/`). The file keeps its own line endings.
* `external_code_upload.md` is also recognised when the repository form wrote the app's Python package name in place of `PYTHON_PROJ_NAME`; the new page gets the same name.
* A guide the app changed is left as it is (`SKIPPED`, with a note to compare it with the template's page). Many apps have their own `troubleshooting.md`, so it is often skipped.
* A missing guide is not created, and nothing is deleted. A second run changes nothing.

## 4. Adopting it

Take this template version (the synchronization pull request). For a skipped guide, compare it with the template's page and take what you want.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_37.py`): the resources are the live guides and differ from the 0.1.36 ones; a 0.1.36 app reaches the live guides with LF and CRLF line endings, and a second run changes nothing; a customised guide is skipped; a missing guide is not created; `external_code_upload.md` with a package name; the sync from 0.1.36 and the chain from older versions.
* The older tests compare with the 0.1.36 guides (`tests/_v0_1_37.py`, `before_0_1_37`).
