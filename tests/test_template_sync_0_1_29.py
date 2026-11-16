"""Tests of the 0.1.29 migration: text corrections, the changelog quotes the commit subject only, design notes leave the docs list."""
from __future__ import annotations

import importlib.util
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

from _v0_1_29 import before_0_1_29


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_28_to_v0_1_29.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_29")
INDEX = MIGRATION.DOCS_INDEX
NOTE_ENTRY = "- [Template 0.1.26: the app's own documentation explains PyPI publishing](migration_0_1_26.md)\n"


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def index_of_0_1_28() -> bytes:
    """The docs README of 0.1.28: the old tools entry, and a design note listed under the template-sync entry."""
    text = before_0_1_29(INDEX, (ROOT / INDEX).read_bytes()).decode("utf-8")
    anchor = "- [Enable automatic template updates](template_synchronization.md)\n"
    return text.replace(anchor, anchor + NOTE_ENTRY, 1).encode("utf-8")


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertRegex(text, r"template_version: 0\.1\.(29|[3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_28_to_v0_1_29.py", text)

    def test_the_live_files_hold_each_correction_once_and_no_old_text(self) -> None:
        for relative, edits in MIGRATION.EDITS.items():
            text = lf(ROOT / relative)
            for old, new in edits:
                with self.subTest(file=str(relative), new=new[:40]):
                    self.assertEqual(text.count(new), 1)
                    self.assertNotIn(old, text)

    def test_the_docs_list_has_no_design_notes_but_the_notes_stay(self) -> None:
        self.assertNotRegex(lf(ROOT / INDEX), r"\(migration_0_1_\d+\.md\)")
        for number in range(16, 29):
            with self.subTest(version=number):
                self.assertTrue((ROOT / f".tools/docs/migration_0_1_{number}.md").is_file())

    def test_the_changelog_script_quotes_the_subject_line(self) -> None:
        text = lf(ROOT / MIGRATION.UPDATE_CHANGELOG)
        self.assertIn("'--pretty=%s'", text)
        self.assertNotIn("%B", text)


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_29_"))
        for relative in MIGRATION.EDITS:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = index_of_0_1_28() if relative == INDEX else before_0_1_29(relative, (ROOT / relative).read_bytes())
            target.write_bytes(data)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()

    def test_an_app_of_0_1_28_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        for relative in MIGRATION.EDITS:
            self.assertNotEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes(), relative)
        log = self.run_migration()
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes())
        self.assertIn("1 design note entries removed from the list", log)
        self.assertIn(f"{len(MIGRATION.EDITS)} file(s) changed", log)
        self.assertIn("\r\n", (self.repo / MIGRATION.POST_INSTALL_BAT).read_bytes().decode("utf-8"), "post_install.bat stays CRLF")
        self.assertIn("no repository changes were required", self.run_migration())

    def test_an_initialised_app_gets_the_log_line_with_its_own_name(self) -> None:
        for relative in (MIGRATION.POST_INSTALL_SH, MIGRATION.POST_INSTALL_BAT):
            path = self.repo / relative
            path.write_bytes(path.read_bytes().replace(b"PROJECT_NAME", b"MyApp").replace(b"PYTHON_PROJ_NAME", b"myapp"))
        self.run_migration()
        self.assertIn('registering the tools of MyApp for Napari, Fiji and QuPath"', lf(self.repo / MIGRATION.POST_INSTALL_SH))
        self.assertIn("registering the tools of MyApp for Napari, Fiji and QuPath.", lf(self.repo / MIGRATION.POST_INSTALL_BAT))

    def test_a_changed_passage_and_missing_files_are_left_alone(self) -> None:
        doc = self.repo / MIGRATION.USE_CASES_DOC
        doc.write_text("# Our own use cases\n", encoding="utf-8")
        (self.repo / MIGRATION.UPDATE_CHANGELOG).unlink()
        log = self.run_migration()
        self.assertEqual(doc.read_text(encoding="utf-8"), "# Our own use cases\n")
        self.assertIn("2 passage(s) differ from the template text and were left as they are", log)
        self.assertIn(f"{MIGRATION.UPDATE_CHANGELOG}: not present in this repository", log)
        self.assertFalse((self.repo / MIGRATION.UPDATE_CHANGELOG).exists())

    def test_the_sync_script_runs_the_migration_from_0_1_28(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.29", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.28", "--to-version", "0.1.29", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.29]", result.stdout)
        self.assertEqual((self.repo / MIGRATION.UPDATE_CHANGELOG).read_bytes(), (ROOT / MIGRATION.UPDATE_CHANGELOG).read_bytes())


if __name__ == "__main__":
    unittest.main()
