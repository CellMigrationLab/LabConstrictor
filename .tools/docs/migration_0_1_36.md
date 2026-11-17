# Template 0.1.36: the plugins are no longer experimental, and the page of examples is gone

Design note for the 0.1.36 migration (`.template_sync/migrations/v0_1_35_to_v0_1_36.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

* The napari, Fiji and QuPath plugins that run an app's tools are an implemented way to use an app, but the template still called them experimental: in the title of `tools_bridge.md`, in its entry in the docs README and in its line in `README.md`.
* The "Examples" section of the guides had one page, `use_cases.md`. It listed only VLab4Mic until 0.1.35, and since then it only pointed to the [App Centre](https://cellmigrationlab.github.io/LabConstrictor-Site/apps/), which lists every app. A page that only links elsewhere is not needed.

## 2. What changes

| File | Change |
|---|---|
| `.tools/docs/tools_bridge.md` | Title "(optional)" instead of "(optional, experimental)". |
| `.tools/docs/README.md` | The tools entry without "(experimental)"; the "Examples" section is removed. |
| `README.md` | The tools line without "(experimental)"; the "See what others have built" line is removed. |
| `.tools/docs/use_cases.md` | Removed. |

Whether an app is experimental is a different thing: the `status` field of `labconstrictor-app.yaml` (`Experimental`, `Available` or `Deprecated`) is unchanged. The website publishes `use_cases.md` as `/guides/use-cases/`; it adds a redirect from that address when this version is merged.

## 3. What the migration does

Every step is independent and idempotent, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`use_cases.md`** is removed when it is still the 0.1.35 template file (compared with LF line endings; the frozen copy is in `.template_sync/resources/v0_1_35_to_v0_1_36/previous/`). An app at 0.1.34 gets there through 0.1.35, which first replaces its unchanged page with the 0.1.35 one. A page the app changed is its own and is kept (`SKIPPED`). This is the only file the migration deletes.
* **`tools_bridge.md`, the docs README and `README.md`**: each change replaces one exact piece of 0.1.35 text. A passage where that text is not found is left as it is (`SKIPPED`), and the other changes of the file are still made. An app that keeps its own `use_cases.md` but has the template's README lines loses those links; the log names both files.

## 4. Adopting it

Take this template version (the synchronization pull request). Nothing else is needed: the docs change only.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_36.py`): the page is gone and its frozen copy is the 0.1.35 page; the live files are the 0.1.35 files migrated; no user page or README links `use_cases.md` or calls the plugins experimental; the migration on 0.1.35 files with LF and CRLF line endings, on a customised page and passage, on a repository without the files, on files that are not text, and a second run; the sync from 0.1.35 and the chain from 0.1.34.
* The older tests read a removed file from its frozen copy (`tests/_v0_1_36.py`, `template_bytes`).
