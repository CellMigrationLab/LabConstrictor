# Template 0.1.33: installers use LabConstrictor-Tools v0.3.0-alpha.3

Design note for the 0.1.33 migration (`.template_sync/migrations/v0_1_32_to_v0_1_33.py`). Context: [LabConstrictor-Tools #163](https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/163).

## Why

LabConstrictor-Tools v0.3.0-alpha.2 wrote a result image with exactly 3 or 4 planes (for example 3 channels or 3 timepoints) as one page of colour
samples. Fiji cannot open such a file unless it is 8-bit, so the result of a tool like *Align channels* on a 3-channel image did not appear in Fiji
(napari showed it). v0.3.0-alpha.3 writes every result image of 3 or more dimensions as grey planes, except an 8-bit colour image
([LabConstrictor-Tools #163](https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/163)).

## What changes in an app repository

* `LC_TOOLS_PIN` in `app/bash_bat_scripts/post_install.sh` and `post_install.bat` moves from `v0.3.0-alpha.2` to `v0.3.0-alpha.3`, only when the
  line still holds the template's old value. A pin you set yourself is left as it is, and the sync log says so.

Nothing else changes. The new pin reaches users with the app's next release. The tag `v0.3.0-alpha.3` must exist before such an installer
is built: an installer that pins a missing tag installs the app without its napari / Fiji / QuPath tools (the installer log says so).
