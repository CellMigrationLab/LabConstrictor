# Template 0.1.34: installers use LabConstrictor-Tools v0.3.0-alpha.4

Design note for the 0.1.34 migration (`.template_sync/migrations/v0_1_33_to_v0_1_34.py`). Context: [LabConstrictor-Tools #165](https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/165).

## Why

With LabConstrictor-Tools v0.3.0-alpha.3, every result image reached Fiji as plain TIFF pages: a corrected 3D time-lapse opened as one long
stack (time points x slices) and had to be turned back into a hyperstack by hand. v0.3.0-alpha.4 writes a result whose axes are known, declared
with `Axes(...)` or returned with the new `WithAxes(array, axes)`, as an ImageJ hyperstack when its axes are in ImageJ order (T, Z, C, Y, X):
Fiji opens it with its time points, slices and channels. The array is never reordered, so napari and notebooks read the same data as before.
A tool uses it by returning its image with `WithAxes`; nothing changes for tools that do not.

## What changes in an app repository

* `LC_TOOLS_PIN` in `app/bash_bat_scripts/post_install.sh` and `post_install.bat` moves from `v0.3.0-alpha.3` to `v0.3.0-alpha.4`, only when the
  line still holds the template's old value. A pin you set yourself is left as it is, and the sync log says so.

Nothing else changes. The new pin reaches users with the app's next release.
