# Template 0.1.35: user docs fixed after a review of the website

Design note for the 0.1.35 migration (`.template_sync/migrations/v0_1_34_to_v0_1_35.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

The website ([LabConstrictor-Site](https://cellmigrationlab.github.io/LabConstrictor-Site/)) publishes the template's `.tools/docs` as its "Build an app" guides and a few user guides. A review of the website on 2026-11-17 found these errors in them:

* `troubleshooting_installed_app.md` sent people to an "uninstalling guide" at `download_executable.md`, which is a stub until an app makes a release. No page said how to uninstall an app, while `install.md` tells macOS and Windows users to uninstall the old version before they update.
* `tools_bridge.md` linked "Writing tools" to `docs/AUTHORING.md` on GitHub; the website now publishes it as [Writing tools](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/writing-tools/), the page people read.
* `notebook_usage.md` said Linux has a Start Menu.
* `use_cases.md` listed one app while the [App Centre](https://cellmigrationlab.github.io/LabConstrictor-Site/apps/) lists every app built with LabConstrictor; a second list drifts.
* `notebook_upload.md` fenced its long Python cell without a language.
* Headings with emoji, Title Case or a trailing colon broke the website's heading style (sentence case, no emoji, no trailing colon); `code_hiding.md` asked "How is this for?".

## 2. What changes

| File | Change |
|---|---|
| `.tools/docs/install.md` | New section "Uninstall an app": on Windows, Settings > Apps > Installed apps or `Uninstall-<AppName>.exe` in the install folder; on macOS and Linux, `bash <install folder>/uninstall.sh`, which removes the app's shortcut, takes the app out of the tools list and deletes the install folder. The update steps link to it. |
| `.tools/docs/troubleshooting_installed_app.md` | Links to that section. |
| `.tools/docs/tools_bridge.md` | Both "Writing tools" links go to the website's guide. |
| `.tools/docs/notebook_usage.md` | Start Menu (Windows), Applications folder (macOS), applications menu (Linux), as the website's [/guides/using-apps/](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/using-apps/) says. |
| `.tools/docs/use_cases.md` | Links to the App Centre instead of keeping its own list. |
| `.tools/docs/notebook_upload.md` | The version-check cell is fenced as `python`. |
| `code_hiding.md`, `before_getting_started.md`, `executable_creation.md`, `workflow_status.md`, `installer_images.md` | Headings in sentence case, without emoji or trailing colons. No page of the template or of the website links to the old anchors. |

The uninstall steps describe what the installer creates: `construct.yaml` ships `uninstall.sh` in the install folder on macOS and Linux, and `post_install.bat` lists the app under Installed apps with `Uninstall-<AppName>.exe` as its uninstaller.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`use_cases.md`** is replaced by the 0.1.35 page when it is still the 0.1.34 template file (compared with LF line endings; the frozen copies are in `.template_sync/resources/v0_1_34_to_v0_1_35/`). An app that wrote its own page keeps it (`SKIPPED`).
* **The other pages**: each change replaces one exact piece of 0.1.34 text (a heading is matched as a whole line). A passage where that text is not found is left as it is (`SKIPPED`), and the other changes of the file are still made.

## 4. Adopting it

Take this template version (the synchronization pull request). Nothing else is needed: the docs change only. Users see the new pages on GitHub at once and in the app with its next release.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_35.py`): the resources are the live page and the 0.1.34 one; the live files are the 0.1.34 files migrated; the uninstall section names what the installer creates; no user page links to the download stub for uninstalling or to `AUTHORING.md` on GitHub; the headings of the changed pages have no emoji or trailing colon; the links and anchors of the changed pages resolve; the migration on 0.1.34 files with LF and CRLF line endings, on customised files, on a repository without the files, and a second run; the sync chain from 0.1.34.
