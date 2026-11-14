# Template 0.1.28: installers use LabConstrictor-Tools v0.3.0-alpha.2

Design note for the 0.1.28 migration (`.template_sync/migrations/v0_1_27_to_v0_1_28.py`). Context: [LabConstrictor-Tools #155](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/155).

## Why

Template 0.1.27 let an app declare `host_requirements` in `labconstrictor-app.yaml` (the oldest napari, Fiji or QuPath plugin it needs). The installer passes that file to `labconstrictor-tools register --app-manifest`, but only Tools v0.3.0-alpha.2 or later copies the block into the registry entry, where the plugins read it. Older Tools ignore it. So the installers must install v0.3.0-alpha.2.

## What the migration does

* `LC_TOOLS_PIN` in `app/bash_bat_scripts/post_install.sh` and `post_install.bat` moves from `v0.3.0-alpha.1` to `v0.3.0-alpha.2`, only when the line still holds exactly the old template value. An app with its own pin, a script without a pin line or without the Tools hook is left as it is, with a note. Line endings are kept.
* `.tools/docs/tools_bridge.md`: the tag `v0.3.0-alpha.1` is replaced by `v0.3.0-alpha.2`.
* Missing files are not created; nothing is deleted; a second run changes nothing.

The new pin reaches users with the app's next release. The tag `v0.3.0-alpha.2` must exist before such an installer is used (the template CI installs from it).

## Tests

`tests/test_template_sync_0_1_28.py`: the template pins the new tag once per script and names it in the guide; a 0.1.27 app reaches the template files and a second run changes nothing; an own pin, a script without the hook and missing files are left alone; the sync chain from 0.1.27. The frozen resources of 0.1.17 and 0.1.18 are compared with the live files through `tests/_v0_1_28.py`, which moves the pin back.
