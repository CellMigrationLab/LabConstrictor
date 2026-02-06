#!/bin/bash
set -e
echo "Running post_install" > "$PREFIX/menuinst_debug.log"
"$PREFIX/bin/python" -m pip install -r "$PREFIX/LabConstrictor/requirements.txt"
PROJECT_ROOT="$PREFIX/LabConstrictor"
if [ -f "$PROJECT_ROOT/setup.py" ]; then
    echo "Found setup.py, installing LabConstrictor package locally" >> "$PREFIX/menuinst_debug.log"
    "$PREFIX/bin/python" -m pip install "$PROJECT_ROOT"
else
    echo "No setup.py detected, skipping local pip install" >> "$PREFIX/menuinst_debug.log"
fi
"$PREFIX/bin/python" "$PREFIX/LabConstrictor/include_path.py" --path "$PREFIX" --files "$PREFIX/LabConstrictor/notebook_launcher.json" --keyword "BASE_PATH_KEYWORD"
"$PREFIX/bin/python" "$PREFIX/LabConstrictor/include_path.py" --path "$PREFIX" --files "$PREFIX/app/pre_uninstall.sh" --keyword "BASE_PATH"
"$PREFIX/bin/python" "$PREFIX/LabConstrictor/include_path.py" --path "$PREFIX" --files "$PREFIX/uninstall.sh" --keyword "BASE_PATH"
"$PREFIX/bin/python" "$PREFIX/LabConstrictor/hide_code_cells.py" "$PREFIX/LabConstrictor"
"$PREFIX/bin/python" -c "import os, sys; print('Python:', sys.executable); print('Prefix:', os.environ.get('PREFIX'))" >> "$PREFIX/menuinst_debug.log"
"$PREFIX/bin/python" -c "from menuinst.api import install; import os; print(install(os.path.join('$PREFIX', 'LabConstrictor', 'notebook_launcher.json')))" >> "$PREFIX/menuinst_debug.log" 2>&1

if [ -t 0 ]; then
    echo
    read -rp "Press Enter to close the installer..." _
fi