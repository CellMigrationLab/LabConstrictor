@ECHO OFF
SETLOCAL
echo Running post_install > "%PREFIX%\menuinst_debug.log"
SET "BASE_REQUIREMENTS=%PREFIX%\PROJECT_NAME\requirements.txt"
SET "GPU_REQUIREMENTS=%PREFIX%\PROJECT_NAME\requirements_gpu.txt"
SET "SELECTED_REQUIREMENTS=%BASE_REQUIREMENTS%"
SET "NVIDIA_SMI="

IF EXIST "%GPU_REQUIREMENTS%" (
    CALL :detect_nvidia_smi
    IF DEFINED NVIDIA_SMI (
        echo NVIDIA GPU utility detected at "%NVIDIA_SMI%", installing GPU requirements from "%GPU_REQUIREMENTS%" >> "%PREFIX%\menuinst_debug.log"
        SET "SELECTED_REQUIREMENTS=%GPU_REQUIREMENTS%"
    ) ELSE (
        echo NVIDIA GPU not detected, installing CPU requirements from "%BASE_REQUIREMENTS%" >> "%PREFIX%\menuinst_debug.log"
    )
) ELSE (
    echo GPU requirements file not found, installing CPU requirements from "%BASE_REQUIREMENTS%" >> "%PREFIX%\menuinst_debug.log"
)

echo Installing requirements from "%SELECTED_REQUIREMENTS%" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -m pip install -r "%SELECTED_REQUIREMENTS%" >> "%PREFIX%\menuinst_debug.log"

IF EXIST "%PREFIX%\PROJECT_NAME\requirements-windows.txt" (
    "%PREFIX%\python.exe" -m pip install -r "%PREFIX%\PROJECT_NAME\requirements-windows.txt" >> "%PREFIX%\menuinst_debug.log"
)

SET "PROJECT_ROOT=%PREFIX%\PROJECT_NAME"
IF EXIST "%PROJECT_ROOT%\setup.py" (
    echo Found setup.py, installing PROJECT_NAME package locally >> "%PREFIX%\menuinst_debug.log"
    "%PREFIX%\python.exe" -m pip install "%PROJECT_ROOT%" >> "%PREFIX%\menuinst_debug.log"
) ELSE (
    echo No setup.py detected, skipping local pip install >> "%PREFIX%\menuinst_debug.log"
)
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\include_path.py" --path "%PREFIX%" --files "%PREFIX%\PROJECT_NAME\notebook_launcher.json" --keyword "BASE_PATH_KEYWORD" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" "%PREFIX%\PROJECT_NAME\hide_code_cells.py" "%PREFIX%\PROJECT_NAME" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -c "import os, sys; print('Python:', sys.executable); print('Prefix:', os.environ.get('PREFIX'))" >> "%PREFIX%\menuinst_debug.log"
"%PREFIX%\python.exe" -c "from menuinst.api import install; import os; print(install(os.path.join(r'%PREFIX%', 'PROJECT_NAME', 'notebook_launcher.json')))" >> "%PREFIX%\menuinst_debug.log" 2>&1

SET "ARP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\UNDERSCORED_PROJECT_NAME"
SET "UNINSTALL_EXE=%PREFIX%\Uninstall-UNDERSCORED_PROJECT_NAME.exe"
SET "DISPLAY_ICON=%PREFIX%\PROJECT_NAME\logo.ico"
SET "DISPLAY_VERSION=VERSION_NUMBER"
SET "PUBLISHER=GITHUB_OWNER"
echo Registering PROJECT_NAME in Windows Apps list >> "%PREFIX%\menuinst_debug.log"
reg add "%ARP_KEY%" /v DisplayName /d "PROJECT_NAME" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v DisplayVersion /d "%DISPLAY_VERSION%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v Publisher /d "%PUBLISHER%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v InstallLocation /d "%PREFIX%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v DisplayIcon /d "%DISPLAY_ICON%" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v UninstallString /d "\"%UNINSTALL_EXE%\"" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v QuietUninstallString /d "\"%UNINSTALL_EXE%\" /S" /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v NoModify /t REG_DWORD /d 1 /f >> "%PREFIX%\menuinst_debug.log" 2>&1
reg add "%ARP_KEY%" /v NoRepair /t REG_DWORD /d 1 /f >> "%PREFIX%\menuinst_debug.log" 2>&1

echo Post-install completed!
ENDLOCAL
GOTO :EOF

:detect_nvidia_smi
FOR %%P IN (
    "%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    "%ProgramW6432%\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    "%SystemRoot%\System32\nvidia-smi.exe"
    "%SystemRoot%\Sysnative\nvidia-smi.exe"
) DO (
    IF NOT DEFINED NVIDIA_SMI IF EXIST "%%~P" SET "NVIDIA_SMI=%%~P"
)
IF DEFINED NVIDIA_SMI GOTO :EOF

FOR /F "delims=" %%I IN ('where.exe nvidia-smi.exe 2^>NUL') DO (
    IF NOT DEFINED NVIDIA_SMI SET "NVIDIA_SMI=%%~fI"
)
GOTO :EOF
