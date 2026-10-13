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
        # the template scripts of 0.1.16 are history: the resources of this migration hold them (the template moved on in 0.1.17)
        source = self.helpers.read_text(self.migration.RESOURCE_ROOT / "app/bash_bat_scripts" / name)
        newline = "\r\n" if "\r\n" in source else "\n"
        return self.helpers.render_template(source, self.replacements, newline).encode()

    def install_manifest_check(self) -> None:
        """The manifest check files as the migration leaves them."""
        for relative in self.migration.MANIFEST_CHECK_FILES:
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((self.migration.RESOURCE_ROOT / relative).read_bytes())

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.migration.migrate(self.repo, {})
        return buffer.getvalue()

    def script(self, name: str) -> Path:
        return self.repo / "app/bash_bat_scripts" / name


class TemplateConsistencyTests(unittest.TestCase):
    def test_resources_exist(self) -> None:
        # A migration's resources are history: the template files move on (0.1.17 changes the post_install scripts and the Tools guide).
        migration = load(MIGRATION_PATH, "migration_0_1_16_resources")
        for relative in migration.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                self.assertTrue((migration.RESOURCE_ROOT / relative).is_file())

    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("to: 0.1.16", text)  # the current template_version is checked by the test of the newest migration
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
        self.install_manifest_check()
        (self.repo / ".tools/docs/tools_bridge.md").write_bytes(
            self.helpers.render_template((self.migration.RESOURCE_ROOT / ".tools/docs/tools_bridge.md").read_text(encoding="utf-8"), self.replacements, "\n").encode()
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
        self.assertEqual(added, {".tools/docs/tools_bridge.md"} | {str(p) for p in self.migration.MANIFEST_CHECK_FILES})

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

    def test_several_shim_packages_are_resolved_by_the_tools_module_name(self) -> None:
        """NucleiSky has src/nucleisky, nucleisky2d, nucleisky3d and nucleisky_lc_tools (no usable setup.py name)."""
        for package in ("demoapp2d", "demoapp3d", "demoapp_lc_tools"):
            (self.repo / "src" / package).mkdir()
            (self.repo / "src" / package / "__init__.py").write_text("", encoding="utf-8")
        self.install_old_scripts()
        self.run_migration()
        self.assertIn("demoapp_lc_tools", self.script("post_install.sh").read_text(encoding="utf-8"))
        self.assertNotIn("PYTHON_PROJ_NAME", self.script("post_install.bat").read_text(encoding="utf-8"))

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

    def test_a_stale_schema_copy_is_replaced_and_the_app_manifest_is_not_touched(self) -> None:
        self.install_old_scripts()
        schema = self.repo / ".tools/schema/labconstrictor-app.schema.json"
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text('{"additionalProperties": false, "properties": {}}\n', encoding="utf-8")
        manifest = self.repo / "labconstrictor-app.yaml"
        before = manifest.read_bytes()
        self.run_migration()
        self.assertEqual(schema.read_bytes(), (ROOT / ".tools/schema/labconstrictor-app.schema.json").read_bytes())
        self.assertEqual(manifest.read_bytes(), before)

    def test_the_sync_entry_point_runs_the_chain_step(self) -> None:
        """The way the Sync workflow runs it: .template_sync/sync.py from 0.1.15 to 0.1.16 on a copy of the repository."""
        self.install_old_scripts()
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"  # sync.py checks the target against the manifest: stop the chain at this step
        manifest.write_text(manifest.read_text(encoding="utf-8").replace("template_version: 0.1.17", "template_version: 0.1.16"), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.15", "--to-version", "0.1.16", "--repository-root", str(self.repo)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.script("post_install.sh").read_bytes(), self.expected("post_install.sh"))


FIXTURES = Path(__file__).resolve().parent / "fixtures/bridge_test_hooks"
PIN = "v0.2.0-rc.1"
UNPINNED = "https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip"
PINNED_PREFIX = "https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/"
DOCS_URL = "https://github.com/CellMigrationLab/LabConstrictor/blob/main/.tools/docs/migration_0_1_16.md"


class PinRewriteTests(MigrationCase):
    """Apps whose hook came from the bridge-test branch (NucleiSky PR 32, VLab4Mic) have the unpinned Tools source: it is pinned."""

    APPS = ("vlab4mic", "ns_pr32")

    def install_fixture(self, app: str, crlf: bool = False) -> dict[str, bytes]:
        originals = {}
        for name in ("post_install.sh", "post_install.bat"):
            data = (FIXTURES / app / name).read_bytes()
            if crlf:
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            self.script(name).write_bytes(data)
            originals[name] = data
        return originals

    def test_the_fixtures_are_the_unpinned_bridge_test_text(self) -> None:
        for app in self.APPS:
            for name in ("post_install.sh", "post_install.bat"):
                text = (FIXTURES / app / name).read_text(encoding="utf-8")
                self.assertIn(UNPINNED, text, f"{app}/{name}")
                self.assertNotIn("LC_TOOLS_PIN", text, f"{app}/{name}")

    def test_the_unpinned_source_of_the_real_apps_is_rewritten_to_the_pinned_tag(self) -> None:
        template_sh = (ROOT / "app/bash_bat_scripts/post_install.sh").read_text(encoding="utf-8")
        self.assertIn(f'LC_TOOLS_PIN="{PIN}"', template_sh, "the tests expect the pin the template scripts carry")
        for app in self.APPS:
            for crlf in (False, True):
                with self.subTest(app=app, crlf=crlf):
                    originals = self.install_fixture(app, crlf)
                    output = self.run_migration()
                    newline = b"\r\n" if crlf else b"\n"
                    sh = self.script("post_install.sh").read_bytes()
                    bat = self.script("post_install.bat").read_bytes()
                    self.assertNotIn(b"refs/heads/main.zip", sh + bat)
                    self.assertIn(("${LC_TOOLS_SPEC:-" + PINNED_PREFIX + "${LC_TOOLS_PIN}.zip}").encode(), sh)
                    self.assertIn(('SET "LC_TOOLS_SPEC=' + PINNED_PREFIX + '%LC_TOOLS_PIN%.zip"').encode(), bat)
                    self.assertIn(f'LC_TOOLS_PIN="{PIN}"'.encode() + newline, sh)
                    self.assertIn(f'SET "LC_TOOLS_PIN={PIN}"'.encode() + newline, bat)
                    # the pin line comes before the line that uses it
                    self.assertLess(sh.index(b"LC_TOOLS_PIN="), sh.index(b"${LC_TOOLS_PIN}"))
                    self.assertLess(bat.index(b"SET \"LC_TOOLS_PIN="), bat.index(b"%LC_TOOLS_PIN%"))
                    # surgical: undoing exactly the rewrite gives back the app's file byte for byte, line endings included
                    for name, data in (("post_install.sh", sh), ("post_install.bat", bat)):
                        restored = b"".join(
                            l for l in data.splitlines(keepends=True)
                            if b"Pinned release tag of labconstrictor-tools" not in l
                            and not l.lstrip().startswith((b"LC_TOOLS_PIN=", b'SET "LC_TOOLS_PIN='))
                        )
                        restored = restored.replace(PINNED_PREFIX.encode() + b"${LC_TOOLS_PIN}.zip", UNPINNED.encode())
                        restored = restored.replace(PINNED_PREFIX.encode() + b"%LC_TOOLS_PIN%.zip", UNPINNED.encode())
                        self.assertEqual(restored, originals[name], name)
                        if crlf:
                            self.assertNotIn(b"\n", data.replace(b"\r\n", b""), name)
                    self.assertIn(f"{migration_tag()} app/bash_bat_scripts/post_install.sh: updated", output)
                    self.assertIn(f"{migration_tag()} app/bash_bat_scripts/post_install.bat: updated", output)
                    if shutil.which("bash") and not crlf:
                        subprocess.run(["bash", "-n", str(self.script("post_install.sh"))], check=True)

    def test_a_second_run_changes_nothing(self) -> None:
        for app in self.APPS:
            with self.subTest(app=app):
                self.install_fixture(app)
                self.run_migration()
                after_first = snapshot(self.repo)
                output = self.run_migration()
                self.assertEqual(snapshot(self.repo), after_first)
                self.assertNotIn("post_install.sh: updated", output)
                self.assertNotIn("post_install.bat: updated", output)

    def test_a_customised_tools_source_is_left_alone_with_a_skipped_line(self) -> None:
        fork = "https://github.com/someone/LabConstrictor-Tools/archive/refs/heads/main.zip"
        variants = {
            "other_url": lambda sh, bat: (sh.replace(UNPINNED, fork), bat.replace(UNPINNED, fork)),
            "other_branch": lambda sh, bat: (sh.replace("refs/heads/main.zip", "refs/heads/dev.zip"), bat.replace("refs/heads/main.zip", "refs/heads/dev.zip")),
            "other_variable": lambda sh, bat: (sh.replace("LC_TOOLS_SPEC:-", "MY_SPEC:-"), bat.replace("IF NOT DEFINED LC_TOOLS_SPEC SET", "SET")),
            "two_sources": lambda sh, bat: (sh + "# old: " + UNPINNED + "\n", bat + "REM old: " + UNPINNED + "\n"),
        }
        for label, edit in variants.items():
            with self.subTest(variant=label):
                self.install_fixture("vlab4mic")
                sh = self.script("post_install.sh").read_text(encoding="utf-8")
                bat = self.script("post_install.bat").read_text(encoding="utf-8")
                new_sh, new_bat = edit(sh, bat)
                self.script("post_install.sh").write_bytes(new_sh.encode())
                self.script("post_install.bat").write_bytes(new_bat.encode())
                before = snapshot(self.repo)
                output = self.run_migration()
                for name in ("post_install.sh", "post_install.bat"):
                    self.assertEqual(hashlib.sha256(self.script(name).read_bytes()).hexdigest(), before[f"app/bash_bat_scripts/{name}"], name)
                    self.assertIn(f"app/bash_bat_scripts/{name}: already has the Tools bridge hook: unchanged. SKIPPED the pin", output)
                self.assertIn(DOCS_URL, output)

    def test_the_template_scripts_are_already_pinned_and_untouched(self) -> None:
        for name in ("post_install.sh", "post_install.bat"):
            self.script(name).write_bytes(self.expected(name))
        before = snapshot(self.repo)
        output = self.run_migration()
        for name in ("post_install.sh", "post_install.bat"):
            self.assertEqual(hashlib.sha256(self.script(name).read_bytes()).hexdigest(), before[f"app/bash_bat_scripts/{name}"])
        self.assertNotIn("SKIPPED the pin", output)
        self.assertNotIn("post_install.sh: updated", output)

    def test_the_pin_is_also_applied_when_the_package_cannot_be_detected(self) -> None:
        shutil.rmtree(self.repo / "src")
        self.install_fixture("ns_pr32")
        output = self.run_migration()
        self.assertNotIn(b"refs/heads/main.zip", self.script("post_install.sh").read_bytes())
        self.assertNotIn(b"refs/heads/main.zip", self.script("post_install.bat").read_bytes())
        self.assertIn("could not tell the app's Python package", output)


def migration_tag() -> str:
    return "[migration 0.1.16]"


class NucleiSkyLikePackageTests(MigrationCase):
    """NucleiSky: src/nucleisky, nucleisky2d, nucleisky3d, a setup.py shim without a name and pyproject.toml with name = "nucleisky"."""

    PYPROJECT = '[build-system]\nrequires = ["setuptools>=68"]\n\n[project]\nname = "{name}"\nversion = "0.0.1"\n'
    SHIM = '"""Compatibility shim."""\n\nfrom setuptools import setup\n\n\nsetup()\n'

    def make_tree(self, packages=("nucleisky", "nucleisky2d", "nucleisky3d"), name="nucleisky") -> None:
        shutil.rmtree(self.repo / "src")
        for package in packages:
            (self.repo / "src" / package).mkdir(parents=True)
            (self.repo / "src" / package / "__init__.py").write_text("", encoding="utf-8")
        (self.repo / "setup.py").write_text(self.SHIM, encoding="utf-8")
        if name is not None:
            (self.repo / "pyproject.toml").write_text(self.PYPROJECT.format(name=name), encoding="utf-8")

    def test_the_project_name_of_pyproject_decides_when_the_other_methods_cannot(self) -> None:
        self.make_tree()
        self.assertEqual(self.helpers.detect_python_package_name(self.repo), "PYTHON_PROJ_NAME", "the 0.1.10 helper still cannot tell")
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "nucleisky")

    def test_the_whole_migration_uses_it(self) -> None:
        self.make_tree()
        self.install_old_scripts()
        output = self.run_migration()
        self.assertIn("nucleisky_lc_tools", self.script("post_install.sh").read_text(encoding="utf-8"))
        self.assertIn("nucleisky_lc_tools", self.script("post_install.bat").read_text(encoding="utf-8"))
        self.assertNotIn("PYTHON_PROJ_NAME", self.script("post_install.sh").read_text(encoding="utf-8"))
        self.assertNotIn("could not tell", output)

    def test_hyphens_become_underscores(self) -> None:
        self.make_tree(packages=("demo_app", "demo_app2d"), name="demo-app")
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "demo_app")

    def test_the_package_directory_must_exist(self) -> None:
        self.make_tree(name="something-else")
        self.assertIsNone(self.migration.detect_package(self.helpers, self.repo))
        (self.repo / "src/something_else").mkdir()  # a directory, but not a package of the project: still accepted only by name
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "something_else")

    def test_no_name_or_no_project_table_or_a_broken_file_decides_nothing(self) -> None:
        for label, content in {
            "no_project_table": '[tool.x]\nname = "nucleisky"\n',
            "no_name": '[project]\nversion = "1"\n',
            "broken": "[project\nname = nucleisky\n",
            "not_an_identifier": '[project]\nname = "nucleisky 2d"\n',
        }.items():
            with self.subTest(case=label):
                self.make_tree(name=None)
                (self.repo / "pyproject.toml").write_text(content, encoding="utf-8")
                self.assertIsNone(self.migration.detect_package(self.helpers, self.repo))

    def test_the_other_methods_keep_priority(self) -> None:
        self.make_tree(packages=("nucleisky", "nucleisky2d", "other_lc_tools"), name="nucleisky")
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "other", "the single tools module still wins")
        self.make_tree(packages=("nucleisky",), name="different")
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "nucleisky", "the single package still wins")
        self.make_tree(packages=("nucleisky", "nucleisky2d"), name="nucleisky")
        (self.repo / "setup.py").write_text('from setuptools import setup\nsetup(name="nucleisky2d")\n', encoding="utf-8")
        self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "nucleisky2d", "a name in setup.py still wins")

    def test_the_fallback_also_works_without_tomllib(self) -> None:
        self.make_tree(name=None)
        (self.repo / "pyproject.toml").write_text('[tool.a]\nname = "wrong"\n\n[project]\n# comment\nname = \'nucleisky\'\n\n[tool.b]\nname = "x"\n', encoding="utf-8")
        saved = sys.modules.get("tomllib", "absent")
        sys.modules["tomllib"] = None  # makes `import tomllib` raise ImportError
        try:
            self.assertEqual(self.migration.detect_package(self.helpers, self.repo), "nucleisky")
        finally:
            if saved == "absent":
                del sys.modules["tomllib"]
            else:
                sys.modules["tomllib"] = saved


class DocsReferenceTests(MigrationCase):
    def test_the_docs_index_entry_goes_right_after_the_external_code_upload_entry(self) -> None:
        self.install_old_scripts()
        self.run_migration()
        lines = (self.repo / ".tools/docs/README.md").read_text(encoding="utf-8").splitlines()
        position = next(i for i, l in enumerate(lines) if "external_code_upload.md" in l)
        self.assertEqual(lines[position + 1], self.migration.INDEX_ENTRY)
        self.assertIn("other.md", lines[position + 2])

    def test_no_message_points_to_a_file_that_is_not_in_the_app_repository(self) -> None:
        """migration_0_1_16.md is a template doc the migration never copies: it may only be named by its GitHub URL."""
        self.install_old_scripts()
        self.script("uninstall.sh").write_text("#!/bin/bash\nrm -rf custom\n", encoding="utf-8")
        output = self.run_migration()
        self.assertIn("uninstall.sh: SKIPPED", output)
        self.assertIn(DOCS_URL, output)
        for text in (output, MIGRATION_PATH.read_text(encoding="utf-8")):
            self.assertEqual(text.count("migration_0_1_16.md"), text.count(DOCS_URL), "every mention must be the full URL")
        self.assertFalse((self.repo / ".tools/docs/migration_0_1_16.md").exists())


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

    def test_the_default_tools_source_is_the_pinned_tag_archive(self) -> None:
        prefix = self.make_prefix("pin")
        self.migrated(prefix)
        calls = prefix / "calls.txt"
        env = {"STUB_CALLS": str(calls), "LC_TOOLS_SPEC": ""}
        result = subprocess.run(["bash", str(self.hook_harness(prefix))], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                env={**{k: v for k, v in os.environ.items() if k != "LC_TOOLS_SPEC"}, **env})
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = calls.read_text(encoding="utf-8")
        self.assertIn("-m pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.2.0-rc.1.zip", recorded)
        self.assertNotIn("heads/main", recorded)

    def test_the_pin_is_written_once_per_script_and_never_a_branch(self) -> None:
        for name in ("post_install.sh", "post_install.bat"):
            text = (ROOT / "app/bash_bat_scripts" / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("v0.2.0-rc.1"), 1, name)
            self.assertNotIn("refs/heads/", text, name)
            self.assertIn("refs/tags/", text, name)

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
