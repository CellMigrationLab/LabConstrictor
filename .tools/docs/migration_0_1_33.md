# Template 0.1.33: Tools v0.3.0-alpha.3, and the right version and icon in the Windows Apps list

Design note for the 0.1.33 migration (`.template_sync/migrations/v0_1_32_to_v0_1_33.py`). Context: [LabConstrictor-Tools #163](https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/163).

## Why

LabConstrictor-Tools v0.3.0-alpha.2 wrote a result image with exactly 3 or 4 planes (for example 3 channels or 3 timepoints) as one page of colour
samples. Fiji cannot open such a file unless it is 8-bit, so the result of a tool like *Align channels* on a 3-channel image did not appear in Fiji
(napari showed it). v0.3.0-alpha.3 writes every result image of 3 or more dimensions as grey planes, except an 8-bit colour image
([LabConstrictor-Tools #163](https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/163)).

On Windows, `post_install.bat` also registers the app in *Settings > Apps*. It wrote the version given when the repository was initialised
(`DISPLAY_VERSION`), which no release ever changed (the release script looked for a `PKG_VERSION` line the script no longer has), and the
icon `logo.ico`, which no installer contains: the Apps list showed, for example, VLab4Mic 0.1.3 after installing 0.1.8, without an icon.

## What changes in an app repository

* `LC_TOOLS_PIN` in `app/bash_bat_scripts/post_install.sh` and `post_install.bat` moves from `v0.3.0-alpha.2` to `v0.3.0-alpha.3`, only when the
  line still holds the template's old value. A pin you set yourself is left as it is, and the sync log says so.
* `post_install.bat` reads the version at install time from the `version:` line of the bundled `construct.yaml` (which each release
  writes), keeping the initialisation value as a fallback, and uses the first `.ico` file the installer copied into the app folder as the
  icon; without one it writes no icon entry. Only the template's exact lines are replaced; a block you changed is left as it is, with a note.

Nothing else changes. Both changes reach users with the app's next release. The tag `v0.3.0-alpha.3` must exist before such an installer
is built: an installer that pins a missing tag installs the app without its napari / Fiji / QuPath tools (the installer log says so).
