# Template 0.1.27: an app can say which plugin version its tools need

Design note for the 0.1.27 migration (`.template_sync/migrations/v0_1_26_to_v0_1_27.py`). Proposal and plan: [LabConstrictor-Tools #155](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/155).

## 1. The problem

Hosts already require a minimum LabConstrictor-Tools inside an app. The other direction was missing: an app could not say that its tools need, for example, LabConstrictor-QuPath 0.1.0-alpha.6 (Replace keeps your own annotations) or LabConstrictor-Fiji 0.1.0-alpha.6 (progress of long trainings in the Log window). People with an older plugin got the old behaviour without being told to update. StarDist2D 1.2 needs both.

## 2. What changes

* **Schema** (`.tools/schema/labconstrictor-app.schema.json`, the App Centre's copy): an optional field `host_requirements`, one entry per plugin (`napari`, `fiji`, `qupath`), each with `min_version` and/or `features`, and optionally `why` and `required`. The installer already passes `labconstrictor-app.yaml` to `labconstrictor-tools register --app-manifest`; Tools with feature `host_requirements_v1` copies the field into the registry entry, and plugins that implement the rule warn when theirs is older.
* **Documentation** (`.tools/docs/app_manifest.md`): the section "Plugin versions your tools need (optional)".

## 3. What the migration does

Each step is independent, idempotent, never deletes and never raises for a customised file.

* The schema copy is replaced by the template's (the template owns it, and a test keeps it equal to the App Centre's). Without this, an app that adds the field fails its manifest check, because the schema rejects unknown fields. A repository without a schema copy is left alone.
* The section goes before "## The automatic check" of `app_manifest.md`; on a page without that heading, before its Previous / Home / Next links, or at its end. A page that has the section is unchanged; line endings are kept.
* `labconstrictor-app.yaml` is not touched: the field is optional and each app decides whether it needs it.

## 4. Tests

`tests/test_template_sync_0_1_27.py`: the frozen resources equal the template's files; the schema accepts a valid declaration and refuses the notebook, an empty entry, a version like `latest` and an unknown key; a 0.1.26 app reaches the template's files and a second run changes nothing; CRLF, a page without the heading, a page without links, missing and unreadable files; the sync chain from 0.1.26.
