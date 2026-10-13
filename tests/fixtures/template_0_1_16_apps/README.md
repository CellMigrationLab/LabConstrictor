Real post_install scripts of apps at template 0.1.16 (the hook of 0.1.16 in its pinned form, which is not byte-identical to the template
text: older comment wording), used by tests/test_template_sync_0_1_17.py:

* `playground/`: CellMigrationLab/LabConstrictor-Playground main (the app whose package imports labconstrictor_tools at module level)
* `nucleisky/`: CellMigrationLab/NucleiSky main (only nucleisky_lc_tools imports it)

The scripts are stored as in the app repositories (the .bat files with CRLF).
