"""Tests of the 0.1.16 migration: add the Tools bridge hooks to the installer scripts of an app repository."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_15_to_v0_1_16.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
OLD_SCRIPTS = Path(__file__).resolve().parent / "fixtures/template_0_1_15_scripts"
SCRIPT_NAMES = ("post_install.sh", "post_install.bat", "pre_uninstall.sh", "pre_uninstall.bat", "uninstall.sh")

CONSTRUCT = """name: Demo_App
version: 1.2.3
icon_image: app/logo/demo.png
extra_files:
- app/menuinst/Welcome.ipynb: DemoApp/notebooks/Welcome.ipynb
- app/menuinst/notebook_launcher.json: DemoApp/notebook_launcher.json
- requirements.txt: DemoApp/requirements.txt
"""


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
        self.migration = load(MIGRATION_PATH, "migration_0_1_16")
        self.helpers = self.migration._load_helpers()
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "app_repo"
        (self.repo / "app/bash_bat_scripts").mkdir(parents=True)
        (self.repo / "src/demoapp").mkdir(parents=True)
        (self.repo / "src/demoapp/__init__.py").write_text("", encoding="utf-8")
        (self.repo / "construct.yaml").write_text(CONSTRUCT, encoding="utf-8")
        (self.repo / "notebooks").mkdir()
        (self.repo / "notebooks/analysis.ipynb").write_text('{"cells": []}\n', encoding="utf-8")
        (self.repo / "labconstrictor-app.yaml").write_text("schema: 1\nname: Demo\n", encoding="utf-8")
        (self.repo / ".tools/docs").mkdir(parents=True)
        (self.repo / ".tools/docs/README.md").write_text(
            "# Docs\n\n- [Upload external code (optional)](external_code_upload.md)\n- [Other](other.md)\n", encoding="utf-8"
        )
        self.replacements = self.helpers.load_replacements(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install_old_scripts(self) -> None:
        """What an app repository holds at 0.1.15: the template scripts with the app's names filled in (BASE_PATH stays a token)."""
        for name in SCRIPT_NAMES:
            source = self.helpers.read_text(OLD_SCRIPTS / name)
            newline = "\r\n" if "\r\n" in source else "\n"
            rendered = self.helpers.render_template(source, self.replacements, newline)
            (self.repo / "app/bash_bat_scripts" / name).write_bytes(rendered.encode())

    def expected(self, name: str) -> bytes:
        """The template script of this version rendered for the app, with the line endings of the app's file."""
        source = self.helpers.read_text(ROOT / "app/bash_bat_scripts" / name)
        newline = "\r\n" if "\r\n" in source else "\n"
        return self.helpers.render_template(source, self.replacements, newline).encode()

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.migration.migrate(self.repo, {})
        return buffer.getvalue()

    def script(self, name: str) -> Path:
        return self.repo / "app/bash_bat_scripts" / name


class TemplateConsistencyTests(unittest.TestCase):
    def test_resources_are_identical_to_the_template_files(self) -> None:
        migration = load(MIGRATION_PATH, "migration_0_1_16_resources")
        for relative in migration.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    (migration.RESOURCE_ROOT / relative).read_bytes(),
                    (ROOT / relative).read_bytes(),
                    "update .template_sync/resources/v0_1_15_to_v0_1_16 when the template file changes",
                )

    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.16", text)
        self.assertIn("script: migrations/v0_1_15_to_v0_1_16.py", text)

    def test_chains_from_every_older_version_reach_0_1_16(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_16")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.14", "0.1.15"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.16")
            self.assertEqual(chain[-1]["to"], "0.1.16", start)
        for entry in manifest["migrations"]:
            self.assertTrue((ROOT / ".template_sync" / entry["script"]).is_file(), entry["script"])

    def test_the_old_fixtures_have_no_hook(self) -> None:
        for name in SCRIPT_NAMES:
            self.assertNotIn("labconstrictor_tools", (OLD_SCRIPTS / name).read_text(encoding="utf-8"), name)


class MigrationBehaviourTests(MigrationCase):
    def test_an_old_app_converges_to_the_template_scripts(self) -> None:
        self.install_old_scripts()
        output = self.run_migration()
        for name in SCRIPT_NAMES:
            with self.subTest(script=name):
                self.assertEqual(self.script(name).read_bytes(), self.expected(name))
        self.assertIn("hook added", output)
        self.assertNotIn("PROJECT_NAME", self.script("pre_uninstall.sh").read_text(encoding="utf-8"))
        self.assertIn('"DemoApp"', self.script("post_install.sh").read_text(encoding="utf-8"))
        self.assertIn("demoapp_lc_tools", self.script("post_install.sh").read_text(encoding="utf-8"))
        self.assertIn("BASE_PATH", self.script("pre_uninstall.sh").read_text(encoding="utf-8"), "BASE_PATH is filled in at install time")
        docs = (self.repo / ".tools/docs/README.md").read_text(encoding="utf-8")
        self.assertIn("(tools_bridge.md)", docs)
        self.assertTrue((self.repo / ".tools/docs/tools_bridge.md").is_file())

    def test_running_twice_changes_nothing(self) -> None:
        self.install_old_scripts()
        self.run_migration()
        after_first = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), after_first)
        self.assertIn("no repository changes were required", output)
        self.assertNotIn("hook added", output)

    def test_apps_that_already_carry_the_hooks_are_left_alone(self) -> None:
        for name in SCRIPT_NAMES:
            self.script(name).write_bytes(self.expected(name))
        (self.repo / ".tools/docs/tools_bridge.md").write_bytes(
            self.helpers.render_template((ROOT / ".tools/docs/tools_bridge.md").read_text(encoding="utf-8"), self.replacements, "\n").encode()
        )
        (self.repo / ".tools/docs/README.md").write_text("- [Tools](tools_bridge.md)\n", encoding="utf-8")
        before = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), before)
        self.assertIn("no repository changes were required", output)

    def test_line_endings_of_each_file_are_kept(self) -> None:
        self.install_old_scripts()
        bat = self.script("post_install.bat")
        pre_bat = self.script("pre_uninstall.bat")
        sh = self.script("post_install.sh")
        pre_bat.write_bytes(pre_bat.read_bytes().replace(b"\n", b"\r\n"))  # LF in the template, CRLF in this app
        sh.write_bytes(sh.read_bytes().replace(b"\n", b"\r\n"))  # an app edited on Windows with autocrlf
        self.run_migration()
        for path in (bat, pre_bat, sh):
            data = path.read_bytes()
            self.assertIn(b"labconstrictor_tools", data, path.name)
            self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), f"{path.name}: lone LF in a CRLF file")
        lf = self.script("pre_uninstall.sh").read_bytes()
        self.assertNotIn(b"\r", lf)

    def test_a_customised_script_is_skipped_with_a_message_and_not_changed(self) -> None:
        self.install_old_scripts()
        self.script("post_install.sh").write_text("#!/bin/bash\necho my own installer\n", encoding="utf-8")
        self.script("pre_uninstall.bat").write_text("@ECHO OFF\r\necho mine\r\n", encoding="utf-8")
        self.script("uninstall.sh").write_text("#!/bin/sh\nrm -rf BASE_PATH\n", encoding="utf-8")
        before = {n: self.script(n).read_bytes() for n in ("post_install.sh", "pre_uninstall.bat", "uninstall.sh")}
        output = self.run_migration()
        for name, data in before.items():
            self.assertEqual(self.script(name).read_bytes(), data, name)
        self.assertEqual(output.count("SKIPPED"), 3)
        # the other scripts were still migrated
        self.assertEqual(self.script("post_install.bat").read_bytes(), self.expected("post_install.bat"))
        self.assertEqual(self.script("pre_uninstall.sh").read_bytes(), self.expected("pre_uninstall.sh"))

    def test_missing_files_are_not_created_and_do_not_fail(self) -> None:
        output = self.run_migration()  # no scripts at all
        self.assertEqual(list((self.repo / "app/bash_bat_scripts").iterdir()), [])
        self.assertEqual(output.count("SKIPPED, file not found"), 5)

    def test_an_unreadable_repository_is_skipped_not_raised(self) -> None:
        (self.repo / "construct.yaml").unlink()
        output = self.run_migration()
        self.assertIn("SKIPPED", output)

    def test_user_files_are_never_touched(self) -> None:
        self.install_old_scripts()
        owned = {
            p: (self.repo / p).read_bytes()
            for p in ("notebooks/analysis.ipynb", "labconstrictor-app.yaml", "src/demoapp/__init__.py", "construct.yaml")
        }
        before_names = set(snapshot(self.repo))
        self.run_migration()
        for p, data in owned.items():
            self.assertEqual((self.repo / p).read_bytes(), data, p)
        added = set(snapshot(self.repo)) - before_names
        self.assertEqual(added, {".tools/docs/tools_bridge.md"})

    def test_the_hooks_are_reported_inert_without_a_tools_module(self) -> None:
        self.install_old_scripts()
        self.assertIn("no <package>_lc_tools module", self.run_migration())
        (self.repo / "src/demoapp_lc_tools").mkdir()
        (self.repo / "src/demoapp_lc_tools/__init__.py").write_text("", encoding="utf-8")
        self.assertIn("app has a <package>_lc_tools module", self.run_migration())

    def test_a_tools_module_next_to_the_package_does_not_hide_the_package_name(self) -> None:
        """Found by the Tools smoke run on NucleiSky: with src/<pkg> and src/<pkg>_lc_tools the 0.1.10 helper cannot name the package."""
        (self.repo / "src/demoapp_lc_tools").mkdir()
        (self.repo / "src/demoapp_lc_tools/__init__.py").write_text("", encoding="utf-8")
        self.install_old_scripts()
        self.run_migration()
        for name in ("post_install.sh", "post_install.bat"):
            text = self.script(name).read_text(encoding="utf-8")
            self.assertIn("demoapp_lc_tools", text, name)
            self.assertNotIn("PYTHON_PROJ_NAME", text, name)

    def test_an_undetectable_package_skips_post_install_but_migrates_the_rest(self) -> None:
        (self.repo / "src/other").mkdir()  # two packages and no setup.py: cannot tell which one is the app
        (self.repo / "src/other/__init__.py").write_text("", encoding="utf-8")
        self.install_old_scripts()
        before = {n: self.script(n).read_bytes() for n in ("post_install.sh", "post_install.bat")}
        output = self.run_migration()
        for name, data in before.items():
            self.assertEqual(self.script(name).read_bytes(), data, name)
        self.assertIn("could not tell the app's Python package", output)
        self.assertEqual(self.script("pre_uninstall.sh").read_bytes(), self.expected("pre_uninstall.sh"))

    def test_the_sync_entry_point_runs_the_chain_step(self) -> None:
        """The way the Sync workflow runs it: .template_sync/sync.py from 0.1.15 to 0.1.16 on a copy of the repository."""
        self.install_old_scripts()
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        result = subprocess.run(
            [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.15", "--to-version", "0.1.16", "--repository-root", str(self.repo)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.script("post_install.sh").read_bytes(), self.expected("post_install.sh"))


@unittest.skipUnless(shutil.which("bash"), "bash is not available")
class MigratedScriptsRunTests(MigrationCase):
    """Run the migrated bash scripts against a stub Python (no installer, no network)."""

    def make_prefix(self, behaviour: str) -> Path:
        prefix = Path(self.tmp.name) / "prefix"
        (prefix / "bin").mkdir(parents=True)
        stub = prefix / "bin/python"
        stub.write_text(
            "#!/bin/bash\n"
            'echo "$@" >> "$STUB_CALLS"\n'
            'case "$*" in\n'
            '  *find_spec*) exit "${STUB_FIND_SPEC:-0}" ;;\n'
            '  *"pip install"*) exit "${STUB_PIP:-0}" ;;\n'
            '  *"labconstrictor_tools register"*) exit "${STUB_REGISTER:-0}" ;;\n'
            '  *"labconstrictor_tools unregister"*) exit "${STUB_UNREGISTER:-0}" ;;\n'
            "esac\nexit 0\n",
            encoding="utf-8",
        )
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return prefix

    def migrated(self, prefix: Path) -> None:
        self.install_old_scripts()
        self.run_migration()
        for name in ("pre_uninstall.sh", "uninstall.sh"):
            path = self.script(name)
            path.write_text(path.read_text(encoding="utf-8").replace("BASE_PATH", str(prefix)), encoding="utf-8")
            shutil.copy(path, prefix / name)

    def run_bash(self, script: Path, env_extra: dict[str, str]) -> subprocess.CompletedProcess:
        env = {**os.environ, **env_extra}
        return subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)

    def test_syntax_of_every_migrated_bash_script(self) -> None:
        self.install_old_scripts()
        self.run_migration()
        for name in ("post_install.sh", "pre_uninstall.sh", "uninstall.sh"):
            result = subprocess.run(["bash", "-n", str(self.script(name))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")

    def hook_harness(self, prefix: Path) -> Path:
        """The post_install hook block alone, in the same shell options as post_install.sh."""
        text = self.script("post_install.sh").read_text(encoding="utf-8")
        start = text.index("# --- Optional: expose the app's tools")
        end = text.index('"$PYTHON_EXE" "$PROJECT_ROOT/include_path.py" --path "$PREFIX" --files "$PROJECT_ROOT/notebook_launcher.json"')
        root = prefix / "DemoApp"
        root.mkdir(exist_ok=True)
        (root / "setup.py").write_text("", encoding="utf-8")
        (root / "construct.yaml").write_text(CONSTRUCT, encoding="utf-8")
        harness = Path(self.tmp.name) / "hook.sh"
        harness.write_text(
            "#!/bin/bash\nset -euo pipefail\n"
            f'PREFIX="{prefix}"\nLOG_FILE="$PREFIX/menuinst_debug.log"\nPYTHON_EXE="$PREFIX/bin/python"\nPROJECT_ROOT="$PREFIX/DemoApp"\n'
            + text[start:end]
            + 'echo "reached the end"\n',
            encoding="utf-8",
        )
        return harness

    def test_the_hook_registers_the_app_and_logs_it(self) -> None:
        prefix = self.make_prefix("ok")
        self.migrated(prefix)
        calls = prefix / "calls.txt"
        result = self.run_bash(self.hook_harness(prefix), {"STUB_CALLS": str(calls), "LC_TOOLS_SPEC": "/tmp/tools.whl"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reached the end", result.stdout)
        recorded = calls.read_text(encoding="utf-8")
        self.assertIn("-m pip install /tmp/tools.whl", recorded)
        self.assertIn('-m labconstrictor_tools register --name DemoApp --prefix', recorded)
        self.assertIn("--module demoapp_lc_tools --version 1.2.3", recorded)
        self.assertIn("Tools registered", (prefix / "menuinst_debug.log").read_text(encoding="utf-8"))

    def test_a_failing_registration_never_fails_the_install(self) -> None:
        prefix = self.make_prefix("fail")
        self.migrated(prefix)
        result = self.run_bash(self.hook_harness(prefix), {"STUB_CALLS": str(prefix / "calls.txt"), "STUB_PIP": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reached the end", result.stdout)
        self.assertIn("WARNING: tool registration failed", (prefix / "menuinst_debug.log").read_text(encoding="utf-8"))

    def test_an_app_without_a_tools_module_skips_the_step(self) -> None:
        prefix = self.make_prefix("none")
        self.migrated(prefix)
        calls = prefix / "calls.txt"
        result = self.run_bash(self.hook_harness(prefix), {"STUB_CALLS": str(calls), "STUB_FIND_SPEC": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("pip install", calls.read_text(encoding="utf-8"))
        self.assertFalse("registering" in (prefix / "menuinst_debug.log").read_text(encoding="utf-8"))

    def test_uninstall_unregisters_and_removes_only_the_prefix(self) -> None:
        prefix = self.make_prefix("ok")
        self.migrated(prefix)
        bystander = Path(self.tmp.name) / "my_data"
        bystander.mkdir()
        (bystander / "results.csv").write_text("keep", encoding="utf-8")
        calls = Path(self.tmp.name) / "calls.txt"
        result = self.run_bash(prefix / "uninstall.sh", {"STUB_CALLS": str(calls)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(prefix.exists())
        self.assertEqual((bystander / "results.csv").read_text(encoding="utf-8"), "keep")
        self.assertIn("labconstrictor_tools unregister --name DemoApp", calls.read_text(encoding="utf-8"))

    def test_a_failed_unregister_warns_but_the_uninstall_goes_on(self) -> None:
        prefix = self.make_prefix("ok")
        self.migrated(prefix)
        home = Path(self.tmp.name) / "lc_home"
        (home / "apps").mkdir(parents=True)
        (home / "apps/DemoApp.json").write_text("{}", encoding="utf-8")
        result = self.run_bash(prefix / "uninstall.sh", {"STUB_CALLS": str(Path(self.tmp.name) / "c.txt"), "STUB_UNREGISTER": "1", "LC_HOME": str(home)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WARNING: could not remove DemoApp from the LabConstrictor tools list", result.stderr)
        self.assertFalse(prefix.exists())
        self.assertTrue((home / "apps/DemoApp.json").exists(), "the registry entry is only reported, never deleted by the script")


if __name__ == "__main__":
    unittest.main()
