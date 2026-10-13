Real post_install scripts of apps that got the Tools bridge hook by hand (bridge-test branch) before template 0.1.16, with the
unpinned Tools source `refs/heads/main.zip`:

* `vlab4mic/`: LabConstrictor-VLab4Mic main (post_install.sh line 88, post_install.bat line 111)
* `ns_pr32/`: CellMigrationLab/NucleiSky pull request 32 (refs/pull/32/head), same lines

Used by tests/test_template_sync_0_1_16.py to check that the 0.1.16 migration pins exactly that source.
