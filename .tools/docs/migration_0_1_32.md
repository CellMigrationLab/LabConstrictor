# Template 0.1.32: the user docs link to the guide that owns a topic

Design note for the 0.1.32 migration (`.template_sync/migrations/v0_1_31_to_v0_1_32.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problem

The LabConstrictor documentation is spread over several repositories, and the same steps were written in several of them. Copies drift: on 2026-11-16 the install steps of the Fiji plugin were on 8 pages, those of the napari plugin on 7, and version numbers of the plugins and of LabConstrictor Tools on 22. The rule agreed for the whole project is that each topic is written on one page, its owner, and every other page links to it. The website ([LabConstrictor-Site](https://cellmigrationlab.github.io/LabConstrictor-Site/)) publishes the owner pages, and it imports the template's `.tools/docs` as its "Build an app" guides.

The owners of the topics this template's docs touched:

| Topic | Owner |
|---|---|
| Install an app; what the installer does; where an app declares its tools | This template (`install.md`, `tools_bridge.md`) |
| Install and open the napari plugin, the Fiji plugin, the QuPath extension | Each plugin's repository (`docs/user-guide.md`), published on the website as `/guides/napari/`, `/guides/fiji/`, `/guides/qupath/` |
| Run an app's tools in image software (overview) | LabConstrictor-Tools `docs/user-guide.md`, published as `/guides/image-software/` |
| Write and test a tool (inputs, outputs, form markers, `check` and `test`) | LabConstrictor-Tools `docs/AUTHORING.md` |

`tools_bridge.md` repeated the plugins' install situation, the list of form markers, the test commands and the Tools pin's version (`v0.3.0-alpha.2`, also in the step that tells maintainers to update "the tag in this paragraph").

## 2. What changes

| File | Change |
|---|---|
| `.tools/docs/tools_bridge.md` | Rewritten around what the template owns: where to declare tools, the order of the installer's steps, the Tools pin (where it is set, `LC_TOOLS_SPEC`, how maintainers move it), what to look at when something fails. It links to the owner guides for writing and testing tools and for the plugins. The pin's version is no longer written in the docs: the scripts are the only place it is set. |
| `.tools/docs/install.md` | "Where the app is listed" writes napari in lower case, as the project does, and ends with a link to the guide that says how to run the tools. |
| `.tools/docs/README.md` | The entry of the tools guide writes napari in lower case. |

The template's own README and the other user pages of `.tools/docs` had no copies of these topics. `app_manifest.md` names a plugin version only as an example value of `host_requirements`, which is the template's own field.

## 3. What the migration does

Every step is independent, idempotent, never deletes, never raises for a customised file (the sync pull request is still created) and keeps the line endings of each file.

* **`tools_bridge.md`** is replaced by the 0.1.32 guide when it is still the 0.1.31 template file (compared with LF line endings; the frozen copies are in `.template_sync/resources/v0_1_31_to_v0_1_32/`). A customised guide is left as it is (`SKIPPED`).
* **`install.md`** and **`README.md`**: each change replaces one exact piece of 0.1.31 text. A file where that text is not found is left as it is (`SKIPPED`).

## 4. Adopting it

Take this template version (the synchronization pull request). Nothing else is needed: the docs change only. Users see the new pages on GitHub at once and in the app with its next release.

## 5. What is checked here

* Tests (`tests/test_template_sync_0_1_32.py`): the resources are the live guide and the 0.1.31 one; the live files are the 0.1.31 files migrated; the migration on 0.1.31 files with LF and CRLF line endings, on customised files, on a repository without the files, and a second run; the sync chain from 0.1.31.
* The migration chain was run on copies of real apps.
