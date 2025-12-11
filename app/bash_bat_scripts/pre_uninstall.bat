@ECHO ON
echo Running pre-uninstall
"%PREFIX%\python.exe" -c "from menuinst.api import remove; import os; remove(os.path.join(r'%PREFIX%', 'PROJECT_NAME', 'notebook_launcher.json'))"
SetLocal EnableDelayedExpansion
