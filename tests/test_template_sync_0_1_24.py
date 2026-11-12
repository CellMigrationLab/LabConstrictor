"""Tests of the 0.1.24 migration: download links for "v" tags (#41), installers only for the supported systems (#42), the app's own kernel (#43)."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

import yaml

from _v0_1_24 import before_0_1_24


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_23_to_v0_1_24.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
PLATFORMS_PATH = ROOT / ".tools/python/release_platforms.py"
DOWNLOAD_TEMPLATE = ROOT / ".tools/templates/download_executable_template.md"
SCHEMA = ROOT / ".tools/schema/labconstrictor-app.schema.json"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_24")
PLATFORMS = load(PLATFORMS_PATH, "release_platforms_0_1_24")
BUMP = MIGRATION.BUMP_VERSION
WORKFLOW = MIGRATION.RELEASE_WORKFLOW
LAUNCHER = MIGRATION.LAUNCHER
NOTE = "> No installer is built for"


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def old(relative: Path) -> str:
    """The 0.1.23 file: the live file without the 0.1.24 change."""
    return before_0_1_24(relative, (ROOT / relative).read_bytes()).decode("utf-8").replace("\r\n", "\n")


def helpers() -> ModuleType:
    return MIGRATION._load("v0_1_9_to_v0_1_10.py", "helpers_for_0_1_24_tests")


def write_manifest(root: Path, platforms: object = None, text: str | None = None) -> None:
    if text is None:
        distribution: dict[str, object] = {"installer": True}
        if platforms is not None:
            distribution["platforms"] = platforms
        text = yaml.safe_dump({"name": "My App", "distribution": distribution})
    (root / "labconstrictor-app.yaml").write_text(text, encoding="utf-8")


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(2[4-9]|[3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_23_to_v0_1_24.py", text)

    def test_chains_from_every_older_version_reach_0_1_24(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_24")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.16", "0.1.20", "0.1.23"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.24")
            self.assertEqual(chain[-1]["to"], "0.1.24", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_24.md)", lf(ROOT / ".tools/docs/README.md"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_24.md").is_file())

    def test_the_resource_is_the_live_platforms_script(self) -> None:
        self.assertEqual((MIGRATION.RESOURCE_ROOT / MIGRATION.PLATFORMS_SCRIPT).read_bytes(), PLATFORMS_PATH.read_bytes())

    def test_the_live_files_are_the_0_1_23_files_migrated(self) -> None:
        self.assertEqual(MIGRATION.apply_blocks(old(BUMP), MIGRATION.BUMP_BLOCKS), lf(ROOT / BUMP))
        self.assertEqual(MIGRATION.apply_blocks(old(LAUNCHER), (MIGRATION.LAUNCHER_BLOCK,)), lf(ROOT / LAUNCHER))
        text, count = MIGRATION.add_tag_lines(old(WORKFLOW))
        self.assertEqual(count, 2)
        self.assertEqual(MIGRATION.build_from_platforms(text), lf(ROOT / WORKFLOW))

    def test_without_platforms_the_matrix_is_the_old_four_builds_in_the_same_order(self) -> None:
        old_matrix = yaml.safe_load(textwrap.dedent(MIGRATION.MATRIX_OLD.split("strategy:\n", 1)[1]))["matrix"]
        self.assertEqual(PLATFORMS.matrix(list(PLATFORMS.BUILDS)), old_matrix)

    def test_every_built_system_is_a_schema_platform(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        names = schema["properties"]["distribution"]["properties"]["platforms"]["items"]["enum"]
        self.assertLessEqual({build.platform for build in PLATFORMS.BUILDS}, set(names))

    def test_every_button_of_the_download_template_belongs_to_a_built_system(self) -> None:
        links = re.findall(r'<a href="([^"]*/releases/download/[^"]*)">', lf(DOWNLOAD_TEMPLATE))
        self.assertEqual(len(links), 6)
        endings = tuple(ending for build in PLATFORMS.BUILDS for ending in build.files)
        for link in links:
            self.assertTrue(link.endswith(endings), link)

    def test_the_workflow_builds_from_the_platforms_job(self) -> None:
        jobs = yaml.safe_load(lf(ROOT / WORKFLOW))["jobs"]
        self.assertEqual(jobs["build-installers"]["needs"], ["bump-version", "platforms"])
        self.assertEqual(jobs["build-installers"]["strategy"]["matrix"], "${{ fromJSON(needs.platforms.outputs.matrix) }}")
        self.assertEqual(jobs["platforms"]["outputs"]["matrix"], "${{ steps.matrix.outputs.matrix }}")
        runs = [step.get("run", "") for step in jobs["platforms"]["steps"]]
        self.assertIn('python .tools/python/release_platforms.py --github-output "$GITHUB_OUTPUT"', runs)
        for job in ("bump-version", "build-installers"):
            with self.subTest(job=job):
                step = next(s["run"] for s in jobs[job]["steps"] if s.get("name") == "Determine release version")
                self.assertLess(step.index('echo "RELEASE_TAG=$RAW"'), step.index('RAW="${RAW#v}"'))


class ReleasePlatformsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def os_names(self) -> list[str]:
        return [build.os_name for build in PLATFORMS.builds(self.root)]

    def test_without_a_manifest_or_platforms_every_system_is_built(self) -> None:
        self.assertEqual(self.os_names(), ["linux", "macos-arm64", "macos-intel", "windows"])
        write_manifest(self.root)
        self.assertEqual(self.os_names(), ["linux", "macos-arm64", "macos-intel", "windows"])
        self.assertEqual(PLATFORMS.skipped_builds(self.root), [])

    def test_only_the_listed_systems_are_built(self) -> None:
        write_manifest(self.root, ["windows-x86_64", "macos-arm64", "linux-x86_64"])
        self.assertEqual(self.os_names(), ["linux", "macos-arm64", "windows"])
        self.assertEqual([build.platform for build in PLATFORMS.skipped_builds(self.root)], ["macos-x86_64"])

    def test_systems_without_a_build_are_ignored_but_some_build_is_required(self) -> None:
        write_manifest(self.root, ["linux-arm64", "linux-x86_64"])
        self.assertEqual(self.os_names(), ["linux"])
        write_manifest(self.root, ["linux-arm64", "windows-arm64"])
        with self.assertRaisesRegex(ValueError, "lists linux-arm64, windows-arm64"):
            PLATFORMS.builds(self.root)

    def test_a_broken_manifest_is_reported(self) -> None:
        write_manifest(self.root, "windows-x86_64")
        with self.assertRaisesRegex(ValueError, "must be a list"):
            PLATFORMS.builds(self.root)
        write_manifest(self.root, text="distribution: [unclosed\n")
        with self.assertRaisesRegex(ValueError, "not valid YAML"):
            PLATFORMS.builds(self.root)

    def test_the_command_writes_the_matrix_for_the_workflow_and_fails_with_the_reason(self) -> None:
        write_manifest(self.root, ["macos-arm64"])
        output = self.root / "github_output"
        with redirect_stdout(StringIO()) as printed:
            self.assertEqual(PLATFORMS.main(["--repository-root", str(self.root), "--github-output", str(output)]), 0)
        self.assertIn("Not built: macos-x86_64 (Macs with an Intel processor)", printed.getvalue())
        key, value = output.read_text(encoding="utf-8").strip().split("=", 1)
        self.assertEqual((key, json.loads(value)), ("matrix", {"include": [{"os_name": "macos-arm64", "runner": "macos-15"}]}))
        write_manifest(self.root, ["linux-arm64"])
        result = subprocess.run([sys.executable, str(PLATFORMS_PATH), "--repository-root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("migration_0_1_24.md", result.stderr)


class BumpVersionTests(unittest.TestCase):
    """bump_version.py of the template, run as the release workflow runs it, on an initialised copy of the download page."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".tools/python").mkdir(parents=True)
        (self.root / ".tools/templates").mkdir(parents=True)
        (self.root / ".tools/docs").mkdir(parents=True)
        for name in ("bump_version.py", "release_platforms.py"):
            shutil.copy(ROOT / ".tools/python" / name, self.root / ".tools/python" / name)
        page = DOWNLOAD_TEMPLATE.read_bytes().decode("utf-8")
        for placeholder, value in (("GITHUB_OWNER", "me"), ("GITHUB_REPO_NAME", "my-app"), ("LOWER_PROJ_NAME", "myapp"), ("PROJECT_NAME", "MyApp")):
            page = page.replace(placeholder, value)
        (self.root / ".tools/templates/download_executable_template.md").write_bytes(page.encode("utf-8"))
        (self.root / ".tools/docs/download_executable.md").write_text("old page\n", encoding="utf-8")
        (self.root / "construct.yaml").write_text('name: MyApp\nversion: "1.0.0"\n', encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def bump(self, version: str, tag: str | None) -> subprocess.CompletedProcess[str]:
        env = {key: value for key, value in os.environ.items() if key != "RELEASE_TAG"}
        if tag is not None:
            env["RELEASE_TAG"] = tag
        return subprocess.run([sys.executable, str(self.root / ".tools/python/bump_version.py"), version], capture_output=True, text=True, env=env)

    def page(self) -> str:
        return lf(self.root / ".tools/docs/download_executable.md")

    def links(self) -> list[str]:
        return re.findall(r'<a href="([^"]+)">', self.page())

    def test_a_v_tag_is_the_folder_of_the_links_and_the_names_keep_the_bare_version(self) -> None:
        result = self.bump("1.2.3", "v1.2.3")
        self.assertEqual(result.returncode, 0, result.stderr)
        links = self.links()
        self.assertEqual(len(links), 6)
        for link in links:
            self.assertRegex(link, r"^https://github\.com/me/my-app/releases/download/v1\.2\.3/MyApp-1\.2\.3-")
        self.assertIn('version: "1.2.3"', lf(self.root / "construct.yaml"))

    def test_without_a_tag_the_links_use_the_version(self) -> None:
        self.assertEqual(self.bump("1.2.3", None).returncode, 0)
        for link in self.links():
            self.assertIn("/releases/download/1.2.3/MyApp-1.2.3-", link)

    def test_a_tag_that_is_not_the_version_is_refused(self) -> None:
        result = self.bump("1.2.3", "v1.2.4")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match the version 1.2.3", result.stderr)

    def test_a_system_that_is_not_built_gets_a_note_instead_of_its_button(self) -> None:
        write_manifest(self.root, ["windows-x86_64", "macos-arm64", "linux-x86_64"])
        self.assertEqual(self.bump("1.2.3", "v1.2.3").returncode, 0)
        page = self.page()
        self.assertNotIn("MacOSX-x86_64", page)
        self.assertEqual(len(self.links()), 4)
        self.assertEqual(page.count(f"{NOTE} Macs with an Intel processor"), 2)
        self.assertNotIn("\nor \n", page)
        self.assertNotIn("\nor\n", page)

    def test_every_system_keeps_its_button_without_platforms(self) -> None:
        write_manifest(self.root)
        self.assertEqual(self.bump("1.2.3", None).returncode, 0)
        self.assertEqual(len(self.links()), 6)
        self.assertNotIn(NOTE, self.page())
        self.assertEqual(self.page().count("\nor \n"), 2)


class DownloadPageFunctionTests(unittest.TestCase):
    """The functions of bump_version.py on a page whose links were written by an earlier release (no template to copy)."""

    def setUp(self) -> None:
        self.bump = load(ROOT / ".tools/python/bump_version.py", "bump_version_0_1_24")

    def test_links_written_for_a_v_tag_are_found_by_the_next_release(self) -> None:
        text = '<a href="https://github.com/me/app/releases/download/v1.2.3/App-1.2.3-Linux-x86_64.sh">'
        self.assertEqual(self.bump.replace_version_placeholder(text, "1.3.0", "v1.3.0"), text.replace("v1.2.3", "v1.3.0").replace("1.2.3", "1.3.0"))
        self.assertIn("/download/1.3.0/App-1.3.0-", self.bump.replace_version_placeholder(text, "1.3.0"))

    def test_no_system_left_out_changes_nothing(self) -> None:
        text = lf(DOWNLOAD_TEMPLATE)
        self.assertEqual(self.bump.drop_unbuilt_buttons(text, []), text)

    def test_the_or_goes_when_the_first_button_becomes_a_note(self) -> None:
        text = '<a href="x/releases/download/1/A-1-MacOSX-arm64.pkg">\n<img src="a">\n</a>\n\nor \n\n<a href="x/releases/download/1/A-1-MacOSX-x86_64.pkg">\n<img src="b">\n</a>\n'
        result = self.bump.drop_unbuilt_buttons(text, [(("-MacOSX-arm64.pkg",), "Apple silicon")])
        self.assertTrue(result.startswith(f"{NOTE} Apple silicon"))
        self.assertNotRegex(result, r"(?m)^\s*or\s*$")
        self.assertIn("MacOSX-x86_64.pkg", result)


class LauncherTests(unittest.TestCase):
    def test_jupyterlab_starts_with_the_environment_kernels_first_even_over_a_user_setting(self) -> None:
        launcher = load(ROOT / LAUNCHER, "launch_jupyter_0_1_24")
        seen: dict[str, str | None] = {}

        def fake_main() -> int:
            seen["value"] = os.environ.get("JUPYTER_PREFER_ENV_PATH")
            return 0

        fake_labapp = SimpleNamespace(main=fake_main)
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp) / "Welcome.ipynb"
            notebook.write_text("{}", encoding="utf-8")
            modules = {"jupyterlab": SimpleNamespace(labapp=fake_labapp), "jupyterlab.labapp": fake_labapp}
            with mock.patch.dict(sys.modules, modules), mock.patch.dict(os.environ, {"JUPYTER_PREFER_ENV_PATH": "0"}), mock.patch.object(sys, "argv", []):
                self.assertEqual(launcher.run_jupyter(notebook), 0)
        self.assertEqual(seen["value"], "1")

    def test_the_variable_is_set_before_jupyterlab_is_imported(self) -> None:
        text = lf(ROOT / LAUNCHER)
        body = text[text.index("def run_jupyter(") :]
        self.assertLess(body.index('os.environ["JUPYTER_PREFER_ENV_PATH"] = "1"'), body.index("from jupyterlab.labapp import main"))


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path, text: str, newline: str = "\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return path

    def put_0_1_23_app(self, newline: str = "\n") -> None:
        for relative in (BUMP, WORKFLOW, LAUNCHER):
            self.put(relative, old(relative), newline)

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_a_0_1_23_app_reaches_the_0_1_24_files_and_a_second_run_changes_nothing(self) -> None:
        self.put_0_1_23_app()
        output = self.run_migration()
        for relative in (BUMP, WORKFLOW, LAUNCHER, MIGRATION.PLATFORMS_SCRIPT):
            with self.subTest(file=str(relative)):
                self.assertRegex(output, rf"{re.escape(str(relative))}: updated")
                self.assertEqual(lf(self.repo / relative), lf(ROOT / relative))
        self.assertNotIn("SKIPPED", output)
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertNotIn("SKIPPED", again)
        self.assertEqual({p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}, before)

    def test_crlf_files_keep_their_line_endings(self) -> None:
        self.put_0_1_23_app("\r\n")
        self.run_migration()
        for relative in (BUMP, WORKFLOW, LAUNCHER):
            with self.subTest(file=str(relative)):
                data = (self.repo / relative).read_bytes()
                self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
                self.assertEqual(data.decode("utf-8").replace("\r\n", "\n"), lf(ROOT / relative))

    def test_a_change_elsewhere_in_bump_version_does_not_stop_the_update(self) -> None:
        """CellPatcher refuses pre-release versions between parse_args() and the X.Y.Z check."""
        own = '    if re.fullmatch(r"\\d+\\.\\d+\\.\\d+(?:a|b|rc)\\d+", args.new_version):\n        sys.exit("pre-release: no installer")\n'
        text = old(BUMP).replace("    args = parser.parse_args()\n", "    args = parser.parse_args()\n" + own, 1)
        path = self.put(BUMP, text)
        self.assertIn(f"{BUMP}: updated", self.run_migration())
        migrated = lf(path)
        self.assertIn(own, migrated)
        self.assertEqual(migrated.replace(own, "", 1), lf(ROOT / BUMP))

    def test_a_customised_download_function_is_skipped_and_left_as_it_is(self) -> None:
        text = old(BUMP).replace("        text = text.replace(previous_version, new_version)\n", "        text = my_replace(text)\n", 1)
        path = self.put(BUMP, text)
        self.assertIn(f"{BUMP}: SKIPPED", self.run_migration())
        self.assertEqual(lf(path), text)

    def test_a_matrix_changed_by_hand_is_kept_and_the_tag_is_still_exported(self) -> None:
        """The Playground removed the Intel Mac build from its matrix."""
        intel = "          - os_name: macos-intel\n            runner: macos-15-intel\n"
        text = old(WORKFLOW).replace(intel, "", 1)
        path = self.put(WORKFLOW, text)
        output = self.run_migration()
        self.assertIn("exports RELEASE_TAG in 2 job(s)", output)
        self.assertIn("SKIPPED the build matrix", output)
        migrated = lf(path)
        self.assertNotIn("platforms:\n", migrated)
        self.assertIn(MIGRATION.MATRIX_OLD.replace(intel, ""), migrated)
        self.assertEqual(migrated.count('echo "RELEASE_TAG=$RAW"'), 2)

    def test_a_workflow_without_any_known_part_is_skipped_and_left_as_it_is(self) -> None:
        text = "name: Release\non: release\njobs: {}\n"
        path = self.put(WORKFLOW, text)
        output = self.run_migration()
        self.assertRegex(output, rf"{re.escape(str(WORKFLOW))}: SKIPPED the release tag.*SKIPPED the build matrix")
        self.assertEqual(lf(path), text)

    def test_a_launcher_without_the_import_is_skipped(self) -> None:
        text = old(LAUNCHER).replace("    from jupyterlab.labapp import main\n", "    from my_lab import main\n", 1)
        path = self.put(LAUNCHER, text)
        self.assertIn(f"{LAUNCHER}: SKIPPED", self.run_migration())
        self.assertEqual(lf(path), text)

    def test_missing_files_are_not_created(self) -> None:
        output = self.run_migration()
        self.assertIn(f"{BUMP}: not present", output)
        self.assertIn(f"{MIGRATION.PLATFORMS_SCRIPT}: SKIPPED: the repository has no .tools/python folder", output)
        self.assertEqual(list(self.repo.rglob("*")), [])

    def test_an_own_platforms_script_is_kept(self) -> None:
        path = self.put(MIGRATION.PLATFORMS_SCRIPT, "print('mine')\n")
        self.assertIn("SKIPPED: the repository has its own release_platforms.py", self.run_migration())
        self.assertEqual(lf(path), "print('mine')\n")


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_23(self) -> None:
        self.put_0_1_23_app()
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.24 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.24", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.23", "--to-version", "0.1.24", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.24]", result.stdout)
        self.assertEqual(lf(self.repo / WORKFLOW), lf(ROOT / WORKFLOW))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
