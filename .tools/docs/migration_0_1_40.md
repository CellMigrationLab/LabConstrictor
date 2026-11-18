# Template 0.1.40: an editorial pass on seven guides

Design note for the 0.1.40 migration (`.template_sync/migrations/v0_1_39_to_v0_1_40.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

A third review of the website found pages that announced what they would explain, narrated their pictures, listed generic benefits or read like a brochure. Two passages also gave readers the wrong thing:

* `install.md`, a page for app users, explained the `hosts:` line of `labconstrictor-app.yaml` and quoted an installer log message;
* `workflow_status.md` told readers to paste the whole log file into an AI assistant, which "explains the error and how to fix" it: overconfident, and the log can hold tokens and private paths.

## 2. What changes

* `notebook_portability.md`: one concrete sentence instead of the benefit list; plainer instructions.
* `before_getting_started.md`: the six feature sections become two paragraphs; the prerequisites (now "What you need"), the token and the `distribution.platforms` sentence of 0.1.39 are kept.
* `external_code_upload.md`: the first step says what to do (a package under `src/` with an `__init__.py`); "Good to know" becomes "Limits and options".
* `code_hiding.md`: a plain first paragraph.
* `install.md`: "Where the app is listed" says only that the app's page in the App Centre names the programs it works in, and links the plugin guide.
* `workflow_status.md`: read the failed step first; an AI assistant can help read the log once tokens, private paths and other sensitive information are removed; check its fix against the error and run the workflow again.
* `tools_bridge.md`: "Apps that declare no tools are not affected" moves from the opening to "What the installer does".

Commands, file names, behaviour and the anchors other pages link to (`install.md#uninstall-an-app`, `external_code_upload.md#4-publish-the-code-on-pypi-optional`, `code_hiding.md#how-does-the-play-button-work`) do not change. No code changes.

## 3. What the migration does

* Each file is replaced by the 0.1.40 page when it is still the template file last shipped, compared with LF line endings (the frozen copies, the 0.1.39 template files, are in `.template_sync/resources/v0_1_39_to_v0_1_40/previous/`). The file keeps its own line endings.
* `external_code_upload.md` is also recognised when the repository form wrote the app's Python package name in place of `PYTHON_PROJ_NAME`; the new page gets the same name.
* A file the app changed is left as it is (`SKIPPED`, with a note of what to change by hand; for most pages nothing is required). `code_hiding.md` and `notebook_portability.md` were changed in the template earlier without a migration, so apps made from an older template have another copy and are skipped.
* A missing file is not created, and nothing is deleted. A second run changes nothing.

## 4. Adopting it

Take this template version (the synchronization pull request). For a skipped file, compare it with the template's page; at least make the `workflow_status.md` change by hand.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_40.py`): the resources are the live files and differ from the 0.1.39 ones; a 0.1.39 app reaches the live files with LF and CRLF line endings, and a second run changes nothing; a customised file is skipped with its note; `external_code_upload.md` with a package name; a missing file is not created; the sync from 0.1.39 and the chain from older versions; the anchors other pages link to still exist.
* The older tests compare with the 0.1.39 files (`tests/_v0_1_40.py`, `before_0_1_40`).
