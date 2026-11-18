# Template 0.1.39: a release builds only the systems the app lists

Design note for the 0.1.39 migration (`.template_sync/migrations/v0_1_38_to_v0_1_39.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

`before_getting_started.md` and `executable_creation.md` said that publishing a release builds installers for Windows, macOS and Linux. A release builds only the systems listed under `distribution.platforms` in `labconstrictor-app.yaml`, and every system only when that list is missing (`.tools/python/release_platforms.py`). A reader who lists fewer systems expected installers that never came.

## 2. What changes

Both intros now say a release builds installers for Windows, macOS and Linux, "or only the systems you list under `distribution.platforms`", and link [`distribution` in the manifest guide](app_manifest.md#distribution-how-people-get-the-app). No code changes.

## 3. What the migration does

* Each of the two files is replaced by the 0.1.39 page when it is still the 0.1.38 template file, compared with LF line endings (the frozen copies are in `.template_sync/resources/v0_1_38_to_v0_1_39/previous/`). The file keeps its own line endings.
* A file the app changed is left as it is (`SKIPPED`, with a note of the sentence to add by hand).
* A missing file is not created, and nothing is deleted. A second run changes nothing.

## 4. Adopting it

Take this template version (the synchronization pull request). For a skipped file, add the sentence by hand or compare it with the template's page.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_39.py`): the resources are the live files and differ from the 0.1.38 ones; a 0.1.38 app reaches the live files with LF and CRLF line endings, and a second run changes nothing; a customised file is skipped with its note; a missing file is not created; the sync from 0.1.38 and the chain from older versions.
* The older tests compare with the 0.1.38 files (`tests/_v0_1_39.py`, `before_0_1_39`).
