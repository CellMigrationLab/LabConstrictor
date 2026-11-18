"""Tests of the 0.1.37 migration: the rewritten user guides replace the 0.1.36 guides that an app has not changed."""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import ModuleType

from _v0_1_36 import before_0_1_36
from _v0_1_38 import before_0_1_38


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_36_to_v0_1_37.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
DOCS = ROOT / ".tools/docs"
# The guides a first-time reader follows to the end: the website checks that each has these level-2 headings.
CRITICAL = ("install.md", "initialise_repository.md", "notebook_requirements.md", "notebook_upload.md", "executable_creation.md")
WANTED = (("what you need", "before you start"), ("check that it worked",), ("if something does not work",))


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_37")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def live(relative: Path) -> bytes:
    """The 0.1.37 template file: the live file without the 0.1.38 change (tests/_v0_1_38.py)."""
    return before_0_1_38(relative, (ROOT / relative).read_bytes())


def previous(relative: Path) -> bytes:
    """The 0.1.36 template file (the frozen copy)."""
    return (MIGRATION.PREVIOUS_ROOT / relative).read_bytes()


def with_version(text: str, version: str) -> str:
    """A copy of the template's .template_sync manifest whose template_version is `version` (sync.py refuses another target)."""
    return re.sub(r"template_version: [0-9.]+", f"template_version: {version}", text)


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(3[7-9]|[4-9][0-9])\b")
        self.assertIn("  - from: 0.1.36\n    to: 0.1.37\n    script: migrations/v0_1_36_to_v0_1_37.py\n", text)

    def test_chains_from_older_versions_reach_0_1_37(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_37")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.16", "0.1.35", "0.1.36"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.37")
            self.assertEqual(chain[-1]["to"], "0.1.37", start)

    def test_the_design_note_exists_and_is_not_in_the_docs_index(self) -> None:
        self.assertIn(".tools/docs/migration_0_1_37.md", MIGRATION_PATH.read_text(encoding="utf-8"))
        self.assertTrue((DOCS / "migration_0_1_37.md").is_file())
        self.assertNotIn("migration_0_1_37.md", lf(DOCS / "README.md"))

    def test_the_resources_are_the_live_guides_and_the_0_1_36_ones(self) -> None:
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((MIGRATION.RESOURCE_ROOT / relative).read_bytes(), live(relative))
                self.assertNotEqual(previous(relative), live(relative))
        resources = sorted(p.relative_to(MIGRATION.RESOURCE_ROOT) for p in MIGRATION.RESOURCE_ROOT.rglob("*") if p.is_file())
        expected = sorted([*MIGRATION.FILES, *(Path("previous") / relative for relative in MIGRATION.FILES)])
        self.assertEqual(resources, expected)

    def test_the_older_tests_see_the_0_1_36_guides(self) -> None:
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual(before_0_1_36(relative, live(relative)), before_0_1_36(relative, previous(relative)))

    def test_the_critical_guides_have_the_sections_the_website_checks(self) -> None:
        for name in CRITICAL:
            headings = [line[3:].strip().lower() for line in lf(DOCS / name).splitlines() if line.startswith("## ")]
            for options in WANTED:
                with self.subTest(guide=name, section=options[0]):
                    self.assertTrue(any(h in options for h in headings))

    def test_install_keeps_the_system_sections_the_website_cuts(self) -> None:
        headings = [line[3:].strip() for line in lf(DOCS / "install.md").splitlines() if line.startswith("## ")]
        for heading in ("Install on Windows", "Install on a Mac", "Install on Linux", "Uninstall an app"):
            self.assertIn(heading, headings)

    def test_the_tools_guide_is_an_entry_point(self) -> None:
        text = lf(DOCS / "tools_bridge.md")
        self.assertIn("](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/writing-tools/)", text)
        self.assertNotIn("This page covers", text)
        self.assertNotIn("Move the pin", text)
        self.assertIn("LC_TOOLS_PIN", text)

    def test_the_footer_of_the_sync_guide_follows_the_docs_index(self) -> None:
        index = re.findall(r"\]\(([a-z_0-9]+\.md)\)", lf(DOCS / "README.md"))
        position = index.index("template_synchronization.md")
        text = lf(DOCS / "template_synchronization.md")
        self.assertIn(f"[← Previous]({index[position - 1]})", text)
        self.assertIn(f"[Next →]({index[position + 1]})", text)

    def test_the_relative_links_of_the_guides_resolve(self) -> None:
        for relative in MIGRATION.FILES:
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", lf(ROOT / relative)):
                if "://" in target:
                    continue
                with self.subTest(file=str(relative), target=target):
                    self.assertTrue(((ROOT / relative).parent / target).resolve().exists())


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_37_"))
        for relative in MIGRATION.FILES:
            self.put(relative, previous(relative))

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def put(self, relative: Path, data: bytes) -> Path:
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()

    def assert_template_state(self) -> None:
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes().replace(b"\r\n", b"\n"), live(relative))

    def test_an_app_of_0_1_36_gets_the_guides_and_a_second_run_changes_nothing(self) -> None:
        log = self.run_migration()
        self.assert_template_state()
        self.assertIn(f"done: {len(MIGRATION.FILES)} file(s) changed", log)
        self.assertNotIn("SKIPPED", log)
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertNotIn("SKIPPED", again)
        self.assert_template_state()

    def test_crlf_is_kept(self) -> None:
        for relative in MIGRATION.FILES:
            self.put(relative, previous(relative).replace(b"\n", b"\r\n"))
        log = self.run_migration()
        self.assertNotIn("SKIPPED", log)
        self.assert_template_state()
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertNotIn(b"\n", (self.repo / relative).read_bytes().replace(b"\r\n", b""))

    def test_a_customised_guide_is_skipped_and_the_others_change(self) -> None:
        relative = Path(".tools/docs/troubleshooting.md")
        own = previous(relative) + b"\n## Our own problem\n\nOur own fix.\n"
        page = self.put(relative, own)
        log = self.run_migration()
        self.assertIn(f"{relative}: SKIPPED: customised (not the 0.1.36 template file)", log)
        self.assertEqual(page.read_bytes(), own)
        self.assertIn(f"done: {len(MIGRATION.FILES) - 1} file(s) changed", log)

    def test_the_external_code_guide_with_the_package_name(self) -> None:
        relative = MIGRATION.EXTERNAL_CODE_DOC
        self.assertIn("PYTHON_PROJ_NAME", previous(relative).decode("utf-8"))
        page = self.put(relative, previous(relative).replace(b"PYTHON_PROJ_NAME", b"celltools"))
        log = self.run_migration()
        self.assertIn(f"{relative}: updated: replaced by the 0.1.37 page (with the package name celltools)", log)
        self.assertEqual(page.read_bytes(), live(relative).replace(b"PYTHON_PROJ_NAME", b"celltools"))
        again = self.run_migration()
        self.assertIn(f"{relative}: unchanged: already up to date", again)
        mixed = previous(relative).replace(b"PYTHON_PROJ_NAME", b"celltools", 1).replace(b"PYTHON_PROJ_NAME", b"other")
        self.put(relative, mixed)
        self.assertIn(f"{relative}: SKIPPED", self.run_migration())

    def test_missing_files_are_not_created(self) -> None:
        for relative in MIGRATION.FILES:
            (self.repo / relative).unlink()
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            self.assertIn(f"{relative}: not present in this repository (nothing was created)", log)
        self.assertEqual([p for p in self.repo.rglob("*") if p.is_file()], [])

    def test_a_file_that_is_not_text_is_skipped_and_kept(self) -> None:
        relative = Path(".tools/docs/install.md")
        self.put(relative, b"\xff\xfe not utf-8")
        log = self.run_migration()
        self.assertIn(f"{relative}: SKIPPED", log)
        self.assertEqual((self.repo / relative).read_bytes(), b"\xff\xfe not utf-8")

    def sync(self, start: str) -> subprocess.CompletedProcess[str]:
        manifest = self.repo / ".template_sync/manifest.yaml"
        if not manifest.exists():
            shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
            # sync.py refuses a target other than the manifest version: pin the copy to 0.1.37 (later templates add migrations).
            manifest.write_text(with_version(manifest.read_text(encoding="utf-8"), "0.1.37"), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", start, "--to-version", "0.1.37", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        return subprocess.run(command, capture_output=True, text=True, env=env, check=False)

    def test_the_sync_script_runs_the_migration_from_0_1_36(self) -> None:
        result = self.sync("0.1.36")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.37]", result.stdout)
        self.assert_template_state()
        again = self.sync("0.1.36")
        self.assertIn("[migration 0.1.37] done: no repository changes were required", again.stdout)

    def test_the_sync_chain_from_0_1_35_reaches_the_live_guides(self) -> None:
        """0.1.36 edits the 0.1.35 tools guide, then 0.1.37 replaces it."""
        relative = Path(".tools/docs/tools_bridge.md")
        self.put(relative, before_0_1_36(relative, previous(relative)))
        self.assertNotEqual((self.repo / relative).read_bytes(), previous(relative))
        result = self.sync("0.1.35")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.repo / relative).read_bytes(), live(relative), result.stdout)


if __name__ == "__main__":
    unittest.main()
