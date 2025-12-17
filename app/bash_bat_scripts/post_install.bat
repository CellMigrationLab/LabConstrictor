@ECHO OFF
echo Running post_install > "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -m pip install -r "%PREFIX%\PROJECT_NAME\requirements.txt"
"%PREFIX%\python.exe" -m pip install "wmi==1.5.1"
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\include_path.py" --path "%PREFIX%" --files "%PREFIX%\PROJECT_NAME\notebook_launcher.json" --keyword "BASE_PATH_KEYWORD"
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\hide_code_cells.py" "%PREFIX%\PROJECT_NAME"
"%PREFIX%\python.exe" -c "import os, sys; print('Python:', sys.executable); print('Prefix:', os.environ.get('PREFIX'))" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -c "from menuinst.api import install; import os; print(install(os.path.join(r'%PREFIX%', 'PROJECT_NAME', 'notebook_launcher.json')))" >> "%PREFIX%\menuinst_debug.log" 2>&1

@REM SET "ARP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PROJECT_NAME"
@REM SET "UNINSTALL_EXE=%PREFIX%\Uninstall-PROJECT_NAME.exe"
@REM SET "DISPLAY_ICON=%PREFIX%\PROJECT_NAME\logo.ico"
@REM IF NOT DEFINED PKG_VERSION (
@REM     SET "PKG_VERSION=VERSION_NUMBER"
@REM )
@REM SET "DISPLAY_VERSION=%PKG_VERSION%"
@REM SET "PUBLISHER=GITHUB_OWNER"
@REM echo Registering PROJECT_NAME in Windows Apps list >> "%PREFIX%\menuinst_debug.log"
@REM reg add "%ARP_KEY%" /v DisplayName /d "PROJECT_NAME" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v DisplayVersion /d "%DISPLAY_VERSION%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v Publisher /d "%PUBLISHER%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v InstallLocation /d "%PREFIX%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v DisplayIcon /d "%DISPLAY_ICON%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v UninstallString /d "\"%UNINSTALL_EXE%\"" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v QuietUninstallString /d "\"%UNINSTALL_EXE%\" /S" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v NoModify /t REG_DWORD /d 1 /f >> "%PREFIX%\menuinst_debug.log" 2>&1
@REM reg add "%ARP_KEY%" /v NoRepair /t REG_DWORD /d 1 /f >> "%PREFIX%\menuinst_debug.log" 2>&1

echo Post-install completed!
SetLocal EnableDelayedExpansion
