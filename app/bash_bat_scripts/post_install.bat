@ECHO OFF
echo Running post_install > "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -m pip install -r "%PREFIX%\PROJECT_NAME\requirements.txt"
"%PREFIX%\python.exe" -m pip install "wmi==1.5.1"
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\include_path.py" --path "%PREFIX%" --files "%PREFIX%\PROJECT_NAME\notebook_launcher.json" --keyword "BASE_PATH_KEYWORD"
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\hide_code_cells.py" "%PREFIX%\PROJECT_NAME"
"%PREFIX%\python.exe" -c "import os, sys; print('Python:', sys.executable); print('Prefix:', os.environ.get('PREFIX'))" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -c "from menuinst.api import install; import os; print(install(os.path.join(r'%PREFIX%', 'PROJECT_NAME', 'notebook_launcher.json')))" >> "%PREFIX%\menuinst_debug.log" 2>&1
SetLocal EnableDelayedExpansion
