Real files of apps at template 0.1.17, as stored in their repositories on main (13 October 2026; the .bat files with their line endings), used by
tests/test_template_sync_0_1_18.py:

* `playground/`: CellMigrationLab/LabConstrictor-Playground (CRLF `.bat`). `release_constructor.yml` is its workflow as it is: customised (no Intel Mac
  build) and already pinned by SHA.
* `nucleisky/`: CellMigrationLab/NucleiSky
* `vlab4mic/`: CellMigrationLab/LabConstrictor-VLab4Mic
* `guessthecondition/`: CellMigrationLab/GuessTheCondition

All four hold the template pin `v0.2.0-rc.1` in both scripts. Their other workflows are byte-identical to the resources of the 0.1.18 migration
(the apps pinned the actions by their own pull requests), so the tests use the resources for that case.

`../template_0_1_17_workflows/` holds the five workflows of template 0.1.17 (unpinned), taken from the template at commit 2dbc5ef.
