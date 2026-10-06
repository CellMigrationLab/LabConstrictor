# Expose your app's tools to Napari and Fiji (optional, experimental: branch `bridge-test`)

If your repository ships Python code (see [Upload external code](external_code_upload.md)), you can declare some of its functions
as **tools**. After installation they appear in a generic **Napari** widget and a generic **Fiji** command, and work from the
command line, with forms generated automatically from the function signatures. Nothing changes for apps that do not declare tools.

1. Add a module named `<your_package>_lc_tools` next to your package under `src/` (so `src/mytool_lc_tools/__init__.py` for
   the package `mytool`). Declare tools in it with typed functions, importing your science code **inside** the functions:

   ```python
   from typing import Annotated
   from labconstrictor_tools import Image, ImageOut, Min, tool

   @tool("Gaussian blur")
   def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
       from mytool.filters import gaussian
       return gaussian(image, sigma)
   ```

   Keep the module light: it is imported to read the tool list, so heavy imports at the top slow every start.
2. The installer (`post_install`) detects the module, installs `labconstrictor-tools` and registers the app
   (`labconstrictor-tools register ...`). `pre_uninstall` unregisters it. A failure in this step is logged to
   `menuinst_debug.log` and never fails the installation. Set `LC_TOOLS_SPEC` to install `labconstrictor-tools` from somewhere
   other than PyPI (a wheel, a git URL, a mirror).
3. Test your tools before releasing: `labconstrictor-tools check --module mytool_lc_tools` and
   `labconstrictor-tools test --module mytool_lc_tools --cases lc_tests/cases.json`.
4. Install the Napari plugin (`napari-labconstrictor`) or the Fiji plugin (`labconstrictor-fiji`) once per machine. Neither is on PyPI or a Fiji update site yet: see the READMEs of
   [napari-labconstrictor](https://github.com/CellMigrationLab/napari-labconstrictor) and [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) for the install commands.
5. Optional: make a long form readable with `Group("...")`, `Advanced()` and `EnabledWhen(...)` markers, and say "nothing found" with `ToolError("no_match", ...)` (see the authoring guide in the Tools repository).

Documentation and source: https://github.com/CellMigrationLab/LabConstrictor-Tools.
The registered version is read from the `version:` line of `construct.yaml`. The Windows hook (`post_install.bat`) has not yet been run on a real Windows computer; if you can help, follow the
[human test protocol](https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/HUMAN_TEST_PROTOCOL.md).
Troubleshooting: `labconstrictor-tools doctor`, `labconstrictor-tools logs`, and `~/.labconstrictor/logs/labconstrictor.log`.
