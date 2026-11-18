# Template 0.1.38: one first-run page for app users, one update page, clearer guides

Design note for the 0.1.38 migration (`.template_sync/migrations/v0_1_37_to_v0_1_38.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

Two reviews of the website, checked against the template, the repository form and the installer, found:

* two first-run pages for app users: the template's `notebook_usage.md` and the website's hand-written "Open and use an app" said half of the same things each;
* two update pages: `keep_app_up_to_date.md` explained the sync workflow and sent the reader on to `template_synchronization.md` for the setup;
* `notebook_requirements.md` said both that the form accepts only `package==version` and that the merge keeps ranges such as `numpy>=1.24` as written, without saying where a range can come from (a `requirements.yaml` edited directly on GitHub);
* `personal_access_token.md` ended with "paste the token into your notebook's `GitHub-token` field", which no page has; it did not say where the token is used, why a classic token with `repo` is needed, nor how to set an expiry or revoke it; `before_getting_started.md` did not mention the token;
* `troubleshooting_installed_app.md` gave template version numbers to app users, who cannot see them;
* `executable_creation.md` did not ask to check the systems to build and that the workflows succeeded (not only finished) before a release;
* `tools_bridge.md`, the first page of the "Connect an app" track, was titled "(optional)"; `app_manifest.md` did not say plainly that `windows-arm64` and `linux-arm64` build nothing; a typo in `notebook_upload.md`.

## 2. What changes

* `notebook_usage.md` is titled "Open and use an app": open the app, the Welcome notebook, run a notebook (code hiding is shown, not linked), the app's example, napari / Fiji / QuPath, results, Colab, updates, closing, and where to look when something fails. Links to the website are absolute.
* `template_synchronization.md` is titled "Keep your app up to date" and holds both pages. This file name was kept because more pages link to it (the sync workflow, the template README, `troubleshooting.md`, the 0.1.12 migration and the website). `keep_app_up_to_date.md` becomes a pointer page and leaves the docs README; the pages that linked it link `template_synchronization.md`.
* The other guides are corrected as listed in section 1. `install.md`, `create_repository.md`, `external_code_upload.md` and `troubleshooting.md` follow the new titles and links.

Sixteen files in `.tools/docs/` change (the list is `FILES` in the migration). No code changes.

## 3. What the migration does

* Each file is replaced by the 0.1.38 page when it is still the 0.1.37 template file, compared with LF line endings (the frozen copies are in `.template_sync/resources/v0_1_37_to_v0_1_38/previous/`). The file keeps its own line endings.
* `keep_app_up_to_date.md` becomes the pointer page only when it is the 0.1.37 template copy. An app's own version stays (`SKIPPED`, with a note that its content is now in `template_synchronization.md`). Nothing is deleted.
* `.tools/docs/README.md` is replaced only when it is the 0.1.37 template file. In most apps the repository form replaced it with the template's README, so it is skipped with a note of what to change by hand.
* `external_code_upload.md` is also recognised when the repository form wrote the app's Python package name in place of `PYTHON_PROJ_NAME`; the new page gets the same name.
* A missing file is not created. A second run changes nothing.

## 4. Adopting it

Take this template version (the synchronization pull request). For a skipped file, compare it with the template's page and take what you want.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_38.py`): the resources are the live files and differ from the 0.1.37 ones; a 0.1.37 app reaches the live files with LF and CRLF line endings, and a second run changes nothing; a customised file, the pointer page and the docs README are skipped with their notes; a missing file is not created; `external_code_upload.md` with a package name; the sync from 0.1.37 and the chain from older versions.
* The older tests compare with the 0.1.37 files (`tests/_v0_1_38.py`, `before_0_1_38`).
