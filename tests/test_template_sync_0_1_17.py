"""Tests of the 0.1.17 migration: install labconstrictor-tools BEFORE the import check of the app package in post_install."""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_16_to_v0_1_17.py"
OLD_MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_15_to_v0_1_16.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
OLD_SCRIPTS = FIXTURES / "template_0_1_15_scripts"
APPS_0_1_16 = FIXTURES / "template_0_1_16_apps"
BRIDGE_TEST = FIXTURES / "bridge_test_hooks"
SCRIPT_NAMES = ("post_install.sh", "post_install.bat")
OLD_PIN = "v0.2.0-rc.1"  # the pin of template 0.1.17 (the resources of this migration)
TEMPLATE_PIN = "v0.3.0-alpha.1"  # the pin of the live template since 0.1.18

CONSTRUCT = """name: Demo_App
version: 1.2.3
icon_image: app/logo/demo.png
extra_files:
- app/menuinst/Welcome.ipynb: DemoApp/notebooks/Welcome.ipynb
- app/menuinst/notebook_launcher.json: DemoApp/notebook_launcher.json
- requirements.txt: DemoApp/requirements.txt
"""

# Lines the migration may remove from a script: the variables and the pip call that move into the new block (nothing else).
REMOVABLE = re.compile(
    r'^(#|REM) (Default source|because the package|is not on PyPI|Pinned release tag)'
    r'|^LC_TOOLS_(PIN|MODULE)="'
    r'|^SET "LC_TOOLS_PIN='
    r'|^IF NOT DEFINED LC_TOOLS_SPEC SET'
    r'|^REM LC_TOOLS_SPEC goes to pip'
    r'|pip install "\$\{LC_TOOLS_SPEC:-'
    r"|subprocess\.call\(\[sys\.executable, '-m', 'pip', 'install', os\.environ\['LC_TOOLS_SPEC'\]\]\)"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self.migration = load(MIGRATION_PATH, "migration_0_1_17")
        self.old_migration = load(OLD_MIGRATION_PATH, "migration_0_1_16_for_0_1_17")
        self.helpers = self.migration._load_helpers()
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "app_repo"
        (self.repo / "app/bash_bat_scripts").mkdir(parents=True)
        (self.repo / "src/demoapp").mkdir(parents=True)
        (self.repo / "src/demoapp/__init__.py").write_text("", encoding="utf-8")
        (self.repo / "construct.yaml").write_text(CONSTRUCT, encoding="utf-8")
        (self.repo / ".tools/docs").mkdir(parents=True)
        self.replacements = self.helpers.load_replacements(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def script(self, name: str) -> Path:
        return self.repo / "app/bash_bat_scripts" / name

    def render(self, source: Path, newline: str | None = None) -> bytes:
        text = self.helpers.read_text(source)
        newline = newline or ("\r\n" if "\r\n" in text else "\n")
        return self.helpers.render_template(text, self.replacements, newline).encode()

    def install_0_1_16_template(self) -> None:
        """What an app repository holds at 0.1.16: the template scripts of 0.1.16 (the resources of that migration), rendered for the app."""
        for name in SCRIPT_NAMES:
            self.script(name).write_bytes(self.render(self.old_migration.RESOURCE_ROOT / "app/bash_bat_scripts" / name))

    def expected(self, name: str) -> bytes:
        # what the 0.1.17 migration converges to: the scripts of template 0.1.17 (its resources). The live template moved on (0.1.18 pin).
        return self.render(self.migration.RESOURCE_ROOT / "app/bash_bat_scripts" / name)

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.migration.migrate(self.repo, {})
        return buffer.getvalue()


class TemplateConsistencyTests(unittest.TestCase):
    def test_resources_are_identical_to_the_template_files(self) -> None:
        """Since template 0.1.18 the live files carry the new Tools pin, so the resources of 0.1.17 (frozen: they are what 0.1.17 delivers)
        must equal the live files except for that pin; the byte-for-byte check against the live files is made for the 0.1.18 resources."""
        migration = load(MIGRATION_PATH, "migration_0_1_17_resources")
        for relative in migration.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                live = (ROOT / relative).read_bytes().replace(TEMPLATE_PIN.encode(), OLD_PIN.encode())
                self.assertEqual((migration.RESOURCE_ROOT / relative).read_bytes(), live)

    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("script: migrations/v0_1_16_to_v0_1_17.py", text)

    def test_chains_from_every_older_version_reach_0_1_17(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_17")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.14", "0.1.15", "0.1.16"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.17")
            self.assertEqual(chain[-1]["to"], "0.1.17", start)
        for entry in manifest["migrations"]:
            self.assertTrue((ROOT / ".template_sync" / entry["script"]).is_file(), entry["script"])

    def test_the_docs_are_linked_and_describe_the_new_order(self) -> None:
        self.assertIn("(migration_0_1_17.md)", (ROOT / ".tools/docs/README.md").read_text(encoding="utf-8"))
        bridge = (ROOT / ".tools/docs/tools_bridge.md").read_text(encoding="utf-8")
        self.assertIn("before* it checks that", bridge)
        self.assertIn("lazily", bridge, "the advice to import labconstrictor_tools lazily stays")

    def test_the_template_scripts_install_tools_once_before_the_import_check(self) -> None:
        sh = (ROOT / "app/bash_bat_scripts/post_install.sh").read_text(encoding="utf-8")
        install = sh.index('-m pip install "${LC_TOOLS_SPEC')
        check = sh.index('-c "import PYTHON_PROJ_NAME;')
        register = sh.index("-m labconstrictor_tools register")
        self.assertLess(sh.index('pip install --no-deps --no-build-isolation'), install)
        self.assertLess(install, check)
        self.assertLess(check, register)
        self.assertEqual(sh.count("-m pip install \"${LC_TOOLS_SPEC"), 1)
        self.assertEqual(sh.count(TEMPLATE_PIN), 1)
        self.assertNotIn(OLD_PIN, sh)
        bat = (ROOT / "app/bash_bat_scripts/post_install.bat").read_bytes().decode()
        self.assertEqual(bat.count("\n"), bat.count("\r\n"), "post_install.bat must stay CRLF")
        self.assertEqual(bat.count(TEMPLATE_PIN), 1)
        self.assertNotIn(OLD_PIN, bat)
        self.assertLess(bat.index("CALL :install_lc_tools"), bat.index('-c "import PYTHON_PROJ_NAME;'))
        self.assertLess(bat.index('-c "import PYTHON_PROJ_NAME;'), bat.index("-m labconstrictor_tools register"))
        self.assertEqual(bat.count("\n:install_lc_tools\r\n"), 1)
        # the subroutine comes after the last way out of the main flow, so the flow can never fall into it
        self.assertGreater(bat.index("\n:install_lc_tools\r\n"), bat.index(":detect_nvidia_smi"))
        self.assertGreater(bat.index("\n:install_lc_tools\r\n"), bat.rindex("EXIT /B"))

    def test_remarks_inside_the_parenthesised_block_of_the_bat_contain_no_cmd_special_characters(self) -> None:
        """cmd.exe reads a whole `IF ... ( ... )` block at once: `)`, `<`, `>` and `&` in a REM line there are a known source of trouble."""
        lines = (ROOT / "app/bash_bat_scripts/post_install.bat").read_bytes().decode().split("\r\n")
        start = next(i for i, l in enumerate(lines) if l.startswith('IF EXIST "%PROJECT_ROOT%\\setup.py" ('))
        end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith(") ELSE ("))
        for line in lines[start:end]:
            if line.strip().upper().startswith("REM "):
                self.assertFalse(set(line.strip()[4:]) & set("()<>&|%^"), line)


class MigrationBehaviourTests(MigrationCase):
    def test_the_0_1_16_template_converges_to_the_0_1_17_template(self) -> None:
        self.install_0_1_16_template()
        output = self.run_migration()
        for name in SCRIPT_NAMES:
            with self.subTest(script=name):
                self.assertEqual(self.script(name).read_bytes(), self.expected(name))
        self.assertIn("post_install.sh: updated", output)
        self.assertIn("post_install.bat: updated", output)

    def test_running_twice_changes_nothing(self) -> None:
        self.install_0_1_16_template()
        self.run_migration()
        after_first = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), after_first)
        self.assertIn("no repository changes were required", output)

    def test_scripts_that_already_carry_the_new_order_are_left_alone(self) -> None:
        for name in SCRIPT_NAMES:
            self.script(name).write_bytes(self.expected(name))
        before = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), before)
        self.assertIn("already installs Tools before the import check", output)

    def test_the_whole_chain_from_0_1_15_reaches_the_0_1_17_template(self) -> None:
        for name in SCRIPT_NAMES + ("pre_uninstall.sh", "pre_uninstall.bat", "uninstall.sh"):
            source = self.helpers.read_text(OLD_SCRIPTS / name)
            newline = "\r\n" if "\r\n" in source else "\n"
            self.script(name).write_bytes(self.helpers.render_template(source, self.replacements, newline).encode())
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"  # sync.py checks the target against the manifest: stop the chain at this step
        manifest.write_text(manifest.read_text(encoding="utf-8").replace("template_version: 0.1.18", "template_version: 0.1.17"), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.15", "--to-version", "0.1.17", "--repository-root", str(self.repo)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in SCRIPT_NAMES:
            self.assertEqual(self.script(name).read_bytes(), self.expected(name), name)

    def test_line_endings_of_each_file_are_kept(self) -> None:
        self.install_0_1_16_template()
        sh, bat = self.script("post_install.sh"), self.script("post_install.bat")
        sh.write_bytes(sh.read_bytes().replace(b"\n", b"\r\n"))  # an app edited on Windows with autocrlf
        bat.write_bytes(bat.read_bytes().replace(b"\r\n", b"\n"))  # an app whose bat is LF (CellTracksColab)
        self.run_migration()
        for path, newline in ((sh, b"\r\n"), (bat, b"\n")):
            data = path.read_bytes()
            self.assertIn(b"LC_TOOLS_READY", data, path.name)
            if newline == b"\r\n":
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), f"{path.name}: lone LF in a CRLF file")
            else:
                self.assertNotIn(b"\r", data, f"{path.name}: CR in an LF file")

    def test_customised_scripts_are_skipped_with_a_message_and_not_changed(self) -> None:
        self.install_0_1_16_template()
        sh = self.script("post_install.sh")
        # the registration block was rewritten by the app: the pip call is no longer in the known form
        sh.write_text(sh.read_text(encoding="utf-8").replace('"$PYTHON_EXE" -m pip install "${LC_TOOLS_SPEC:-', '"$PYTHON_EXE" -m pip install --upgrade "${LC_TOOLS_SPEC:-'), encoding="utf-8")
        bat = self.script("post_install.bat")
        bat.write_bytes(bat.read_bytes().replace(b"-m labconstrictor_tools register", b"-m labconstrictor_tools register --verbose", 1).replace(b"GOTO :EOF\r\n", b"GOTO :fail\r\n"))
        before = {n: self.script(n).read_bytes() for n in SCRIPT_NAMES}
        output = self.run_migration()
        self.assertEqual(output.count("SKIPPED"), 2, output)
        for name, data in before.items():
            self.assertEqual(self.script(name).read_bytes(), data, name)
        self.assertIn("migration_0_1_17.md", output, "the message points to the doc by its URL")

    def test_a_script_without_the_hook_or_without_the_import_check_is_not_touched(self) -> None:
        self.script("post_install.sh").write_text("#!/bin/bash\necho my own installer\n", encoding="utf-8")
        self.script("post_install.bat").write_bytes(b"@ECHO OFF\r\necho mine\r\nEXIT /B 0\r\n")
        before = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), before)
        self.assertNotIn("Traceback", output)
        self.assertIn("nothing to move", output)

    def test_missing_files_are_not_created_and_do_not_fail(self) -> None:
        output = self.run_migration()
        self.assertEqual([p.name for p in (self.repo / "app/bash_bat_scripts").iterdir()], [])
        self.assertIn("SKIPPED, file not found", output)

    def test_only_known_lines_are_removed_and_user_lines_stay(self) -> None:
        self.install_0_1_16_template()
        sh, bat = self.script("post_install.sh"), self.script("post_install.bat")
        sh.write_text(sh.read_text(encoding="utf-8").replace('echo "Running post_install"', 'echo "Running post_install"\necho "MY OWN LINE"'), encoding="utf-8")
        bat.write_bytes(bat.read_bytes().replace(b"SET \"SELECTED_REQUIREMENTS=%BASE_REQUIREMENTS%\"\r\n", b"SET \"SELECTED_REQUIREMENTS=%BASE_REQUIREMENTS%\"\r\nREM MY OWN LINE\r\n"))
        before = {n: self.script(n).read_text(encoding="utf-8").splitlines() for n in SCRIPT_NAMES}
        self.run_migration()
        for name in SCRIPT_NAMES:
            after = self.script(name).read_text(encoding="utf-8").splitlines()
            self.assertIn("MY OWN LINE", "\n".join(after))
            removed = [l[2:].strip() for l in difflib.ndiff(before[name], after) if l.startswith("- ")]
            for line in removed:
                self.assertRegex(line, REMOVABLE, f"{name}: the migration removed a line it does not know")

    def test_the_tools_guide_is_refreshed_only_if_it_exists(self) -> None:
        self.install_0_1_16_template()
        output = self.run_migration()
        self.assertIn("not present in this repository", output)
        self.assertFalse((self.repo / ".tools/docs/tools_bridge.md").exists())
        (self.repo / ".tools/docs/tools_bridge.md").write_text("old guide\n", encoding="utf-8")
        self.run_migration()
        self.assertEqual((self.repo / ".tools/docs/tools_bridge.md").read_bytes(), self.render(self.migration.RESOURCE_ROOT / ".tools/docs/tools_bridge.md", "\n"))


class RealAppScriptsTests(MigrationCase):
    """Scripts of real apps (their text as stored in their repositories), with different hooks."""

    def cases(self):
        yield "playground (0.1.16, pinned)", APPS_0_1_16 / "playground", True
        yield "nucleisky (0.1.16, pinned, older comment wording)", APPS_0_1_16 / "nucleisky", True
        yield "vlab4mic (hand-integrated, unpinned)", BRIDGE_TEST / "vlab4mic", False
        yield "nucleisky pull request 32 (hand-integrated, unpinned)", BRIDGE_TEST / "ns_pr32", False

    def test_each_app_gets_the_new_order_and_nothing_else_changes(self) -> None:
        for label, folder, pinned in self.cases():
            for crlf in (False, True):
                with self.subTest(app=label, crlf=crlf):
                    before = {}
                    for name in SCRIPT_NAMES:
                        data = (folder / name).read_bytes()
                        if crlf and name.endswith(".sh"):
                            data = data.replace(b"\n", b"\r\n")
                        self.script(name).write_bytes(data)
                        before[name] = data.decode().splitlines()
                    output = self.run_migration()
                    self.assertEqual(output.count("updated: Tools are installed before the import check"), 2, output)
                    sh = self.script("post_install.sh").read_bytes().decode()
                    bat = self.script("post_install.bat").read_bytes().decode()
                    # order: the Tools install comes before the import check, the registration after it
                    install, register = (sh.index(x) for x in ('-m pip install "${LC_TOOLS_SPEC', '-m labconstrictor_tools register'))
                    check = re.search(r'-c "import (?!importlib)', sh).start()  # the import check of the package
                    self.assertLess(install, check)
                    self.assertLess(check, register)
                    bat_check = re.search(r'-c "import (?!importlib|os)', bat).start()
                    self.assertLess(bat.index("CALL :install_lc_tools"), bat_check)
                    self.assertLess(bat_check, bat.index("-m labconstrictor_tools register"))
                    self.assertEqual(sh.count("-m pip install \"${LC_TOOLS_SPEC"), 1)
                    self.assertEqual(bat.count("'pip', 'install'"), 1)
                    # the app's own Tools source and pin are kept, not replaced by a template default
                    self.assertEqual("LC_TOOLS_PIN=" in sh, pinned)
                    self.assertEqual("LC_TOOLS_PIN=" in bat, pinned)
                    self.assertEqual("refs/heads/main.zip" in sh, not pinned)
                    self.assertEqual("refs/heads/main.zip" in bat, not pinned)
                    self.assertEqual(sh.count("LC_TOOLS_MODULE="), 1)
                    self.assertEqual(bat.count("find_spec("), 2)
                    # line endings
                    for name, text in (("post_install.sh", sh), ("post_install.bat", bat)):
                        crlf_file = b"\r\n" in (folder / name).read_bytes() or (crlf and name.endswith(".sh"))
                        if crlf_file:
                            self.assertEqual(text.count("\n"), text.count("\r\n"), name)
                        else:
                            self.assertNotIn("\r", text, name)
                        after = text.splitlines()
                        for line in (l[2:].strip() for l in difflib.ndiff(before[name], after) if l.startswith("- ")):
                            self.assertRegex(line, REMOVABLE, f"{label} {name}: {line}")
                    # second run: nothing changes
                    snap = snapshot(self.repo)
                    self.assertIn("no repository changes were required", self.run_migration())
                    self.assertEqual(snapshot(self.repo), snap)

    @unittest.skipUnless(shutil.which("bash"), "bash is not available")
    def test_migrated_bash_scripts_of_real_apps_have_valid_syntax(self) -> None:
        for label, folder, _ in self.cases():
            with self.subTest(app=label):
                for name in SCRIPT_NAMES:
                    self.script(name).write_bytes((folder / name).read_bytes())
                self.run_migration()
                result = subprocess.run(["bash", "-n", str(self.script("post_install.sh"))], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(shutil.which("bash"), "bash is not available")
class MigratedPostInstallRunsTests(MigrationCase):
    """Run post_install.sh (migrated, and the 0.1.16 one for comparison) in a sandbox with a fake app package that imports labconstrictor_tools at module level.

    The sandbox is a prefix whose bin/python is a shim: `pip install` creates fake packages in a site folder (no network, no real pip), `-c` and
    `-m labconstrictor_tools` run the real interpreter with that site folder on its path, so the import check really fails or passes."""

    SHIM = textwrap.dedent(
        """\
        #!/bin/bash
        # fake interpreter of the sandbox prefix; every call is recorded in $PREFIX/calls.txt
        PREFIX_DIR="$(cd "$(dirname "$0")/.." && pwd)"
        SITE="$PREFIX_DIR/site"
        echo "$*" >> "$PREFIX_DIR/calls.txt"
        case "$*" in
          *--print-ca-bundle*) echo "$PREFIX_DIR/ca.pem"; exit 0 ;;
          "-m pip install -r "*) exit 0 ;;
          "-m pip install --no-deps --no-build-isolation "*)
              mkdir -p "$SITE"; cp -r "${@: -1}"/src/. "$SITE"/; exit 0 ;;
          "-m pip install "*)
              [ -n "${STUB_TOOLS_PIP_FAILS:-}" ] && { echo "ERROR: no matching distribution" >&2; exit 1; }
              mkdir -p "$SITE/labconstrictor_tools"
              printf 'def tool(*args, **kwargs):\\n    return None\\n' > "$SITE/labconstrictor_tools/__init__.py"
              cat > "$SITE/labconstrictor_tools/__main__.py" <<'PY'
        import importlib, os, sys
        args = sys.argv[1:]
        module = args[args.index("--module") + 1]
        importlib.import_module(module)  # like the real register: it reads the tool list from the module
        with open(os.path.join(os.environ["PREFIX"], "registered.txt"), "a") as handle:
            handle.write(" ".join(args) + "\\n")
        PY
              exit 0 ;;
          *menuinst*|*conda*|*include_path.py*|*hide_code_cells.py*|*launch_jupyter.py*) exit 0 ;;
        esac
        # -S: no site-packages, so a labconstrictor_tools installed in the machine running the tests cannot hide the failure
        PYTHONPATH="$SITE" exec "$REAL_PYTHON" -S "$@"
        """
    )

    def build_prefix(self, package_source: str, tools_source: str = "from labconstrictor_tools import tool\n") -> Path:
        prefix = Path(self.tmp.name) / "prefix"
        (prefix / "bin").mkdir(parents=True)
        shim = prefix / "bin/python"
        shim.write_text(self.SHIM, encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
        (prefix / "ca.pem").write_text("pem\n", encoding="utf-8")
        root = prefix / "DemoApp"
        (root / "src/demoapp").mkdir(parents=True)
        (root / "src/demoapp/__init__.py").write_text(package_source, encoding="utf-8")
        (root / "src/demoapp_lc_tools").mkdir()
        (root / "src/demoapp_lc_tools/__init__.py").write_text(tools_source, encoding="utf-8")
        (root / "setup.py").write_text("", encoding="utf-8")
        (root / "construct.yaml").write_text(CONSTRUCT, encoding="utf-8")
        (root / "requirements.txt").write_text("", encoding="utf-8")
        for name in ("launch_jupyter.py", "include_path.py", "hide_code_cells.py"):
            (root / name).write_text("", encoding="utf-8")
        return prefix

    def run_post_install(self, prefix: Path, script_bytes: bytes, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        script = Path(self.tmp.name) / "post_install_under_test.sh"
        script.write_bytes(script_bytes)
        env = {k: v for k, v in os.environ.items() if k not in ("LC_TOOLS_SPEC", "PYTHONPATH")}
        env.update({"PREFIX": str(prefix), "REAL_PYTHON": sys.executable, **(extra_env or {})})
        return subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)

    def migrated_script(self) -> bytes:
        self.install_0_1_16_template()
        self.run_migration()
        return self.script("post_install.sh").read_bytes()

    def old_script(self) -> bytes:
        self.install_0_1_16_template()
        return self.script("post_install.sh").read_bytes()

    @staticmethod
    def calls(prefix: Path) -> list[str]:
        return (prefix / "calls.txt").read_text(encoding="utf-8").splitlines()

    @staticmethod
    def index(calls: list[str], needle: str) -> int:
        return next(i for i, c in enumerate(calls) if needle in c)

    TOP_LEVEL = "import labconstrictor_tools\n"
    LAZY = "def run():\n    import labconstrictor_tools\n    return labconstrictor_tools\n"

    def test_the_0_1_16_script_fails_for_a_package_that_imports_tools_at_the_top(self) -> None:
        """The reported problem, reproduced: the import check runs before Tools is installed."""
        prefix = self.build_prefix(self.TOP_LEVEL)
        result = self.run_post_install(prefix, self.old_script())
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("ModuleNotFoundError", (prefix / "menuinst_debug.log").read_text(encoding="utf-8"))
        self.assertFalse((prefix / "registered.txt").exists())

    def test_the_migrated_script_installs_tools_first_and_the_install_completes(self) -> None:
        prefix = self.build_prefix(self.TOP_LEVEL)
        result = self.run_post_install(prefix, self.migrated_script())
        log = (prefix / "menuinst_debug.log").read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + log)
        self.assertIn("Post-install completed successfully.", log)
        self.assertIn("DemoApp import successful", log)
        self.assertNotIn("ModuleNotFoundError", log)
        calls = self.calls(prefix)
        package = self.index(calls, "pip install --no-deps --no-build-isolation")
        tools = self.index(calls, "pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.2.0-rc.1.zip")
        check = self.index(calls, "import demoapp;")
        register = self.index(calls, "-m labconstrictor_tools register")
        self.assertLess(package, tools, "the package is installed first: the tools module must be findable")
        self.assertLess(tools, check, "Tools before the import check")
        self.assertLess(check, register, "registration after the import check")
        self.assertEqual(len([c for c in calls if "pip install https://" in c]), 1, "Tools are installed once")
        self.assertIn("--module demoapp_lc_tools --version 1.2.3", (prefix / "registered.txt").read_text(encoding="utf-8"))
        self.assertIn("Tools registered", log)

    def test_lc_tools_spec_still_overrides_the_source(self) -> None:
        prefix = self.build_prefix(self.TOP_LEVEL)
        result = self.run_post_install(prefix, self.migrated_script(), {"LC_TOOLS_SPEC": "/tmp/tools.whl"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls(prefix)
        self.assertIn("-m pip install /tmp/tools.whl", calls)
        self.assertFalse(any("archive/refs" in c for c in calls))

    def test_a_failed_tools_install_is_a_warning_and_the_install_completes_for_a_package_that_does_not_need_tools(self) -> None:
        prefix = self.build_prefix(self.LAZY)
        result = self.run_post_install(prefix, self.migrated_script(), {"STUB_TOOLS_PIP_FAILS": "1"})
        log = (prefix / "menuinst_debug.log").read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + log)
        self.assertIn("WARNING: labconstrictor-tools could not be installed", log)
        self.assertIn("DemoApp import successful", log)
        self.assertIn("Post-install completed successfully.", log)
        self.assertFalse((prefix / "registered.txt").exists(), "nothing is registered without Tools")
        self.assertFalse(any("labconstrictor_tools register" in c for c in self.calls(prefix)))

    def test_a_failed_tools_install_still_fails_a_package_that_needs_tools_at_import_time(self) -> None:
        """Honest behaviour: the WARNING is logged, and the import check (which the package cannot pass without Tools) is what fails."""
        prefix = self.build_prefix(self.TOP_LEVEL)
        result = self.run_post_install(prefix, self.migrated_script(), {"STUB_TOOLS_PIP_FAILS": "1"})
        log = (prefix / "menuinst_debug.log").read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("WARNING: labconstrictor-tools could not be installed", log)

    def test_an_app_without_a_tools_module_does_not_install_tools(self) -> None:
        prefix = self.build_prefix(self.LAZY)
        shutil.rmtree(prefix / "DemoApp/src/demoapp_lc_tools")
        result = self.run_post_install(prefix, self.migrated_script())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any("pip install https://" in c or "labconstrictor_tools" in c.replace("find_spec", "") for c in self.calls(prefix)))
        self.assertFalse((prefix / "registered.txt").exists())

    def test_the_template_script_itself_runs_in_the_same_order(self) -> None:
        prefix = self.build_prefix(self.TOP_LEVEL)
        result = self.run_post_install(prefix, self.expected("post_install.sh"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + (prefix / "menuinst_debug.log").read_text(encoding="utf-8"))
        calls = self.calls(prefix)
        self.assertLess(self.index(calls, "pip install https://"), self.index(calls, "import demoapp;"))
        self.assertLess(self.index(calls, "import demoapp;"), self.index(calls, "-m labconstrictor_tools register"))


if __name__ == "__main__":
    unittest.main()
