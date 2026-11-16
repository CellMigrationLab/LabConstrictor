"""Tests of the 0.1.30 migration: the website's GitHub Pages address, the VLab4Mic logo address, the sentence on Windows and macOS."""
from __future__ import annotations

import importlib.util
import json
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

from _v0_1_30 import before_0_1_30


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_29_to_v0_1_30.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_30")
OLD, NEW = MIGRATION.OLD_URL, MIGRATION.NEW_URL
TEMPLATE_FILES = (*MIGRATION.ADDRESS_FILES, *MIGRATION.EDITS)
EDITOR = "# yaml-language-server: $schema="
APP_MANIFEST_BEFORE = (
    f"{EDITOR}{OLD}schema/labconstrictor-app.schema.json\nschema: 1\nname: My App\nhomepage: {OLD}apps/my-app/\n"
)
PROJECT_FILE_BEFORE = f"{EDITOR}{OLD}schema/labconstrictor-project.schema.json\nname: My App\n"


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertRegex(text, r"template_version: 0\.1\.(30|3[1-9]|[4-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_29_to_v0_1_30.py", text)

    def test_no_live_template_file_names_the_old_address(self) -> None:
        for folder in (".tools", "app", ".github"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.is_file() and path.suffix in {".md", ".json", ".yaml", ".yml", ".py", ".sh", ".bat"}:
                    with self.subTest(file=str(path.relative_to(ROOT))):
                        self.assertNotIn(OLD, path.read_bytes().decode("utf-8", errors="replace"))
        for relative in MIGRATION.ADDRESS_FILES:
            with self.subTest(file=str(relative)):
                self.assertIn(NEW, lf(ROOT / relative))

    def test_the_live_files_hold_each_correction_once_and_no_old_text(self) -> None:
        for relative, edits in MIGRATION.EDITS.items():
            text = lf(ROOT / relative)
            for old, new in edits:
                with self.subTest(file=str(relative), new=new[:40]):
                    self.assertEqual(text.count(new), 1)
                    self.assertNotIn(old, text)

    def test_the_schema_copy_is_valid_json_with_the_new_id(self) -> None:
        schema = json.loads((ROOT / MIGRATION.SCHEMA).read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], NEW + "schema/labconstrictor-app.schema.json")


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_30_"))
        for relative in TEMPLATE_FILES:
            self.put(relative, before_0_1_30(relative, (ROOT / relative).read_bytes()))
        self.put(MIGRATION.APP_MANIFEST, APP_MANIFEST_BEFORE.encode("utf-8"))
        self.put(MIGRATION.PROJECT_FILE, PROJECT_FILE_BEFORE.encode("utf-8"))

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def put(self, relative: Path, data: bytes) -> None:
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()

    def test_an_app_of_0_1_29_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        for relative in TEMPLATE_FILES:
            self.assertNotEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes(), relative)
        log = self.run_migration()
        for relative in TEMPLATE_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes())
        self.assertIn(f"{len(MIGRATION.FILES)} file(s) changed", log)
        self.assertIn("no repository changes were required", self.run_migration())

    def test_only_the_editor_line_of_the_apps_own_files_changes(self) -> None:
        self.run_migration()
        self.assertEqual(
            lf(self.repo / MIGRATION.APP_MANIFEST),
            f"{EDITOR}{NEW}schema/labconstrictor-app.schema.json\nschema: 1\nname: My App\nhomepage: {OLD}apps/my-app/\n",
        )
        self.assertEqual(lf(self.repo / MIGRATION.PROJECT_FILE), f"{EDITOR}{NEW}schema/labconstrictor-project.schema.json\nname: My App\n")

    def test_an_app_file_without_the_editor_line_is_left_alone(self) -> None:
        own = b"schema: 1\nname: My App\n"
        self.put(MIGRATION.APP_MANIFEST, own)
        log = self.run_migration()
        self.assertEqual((self.repo / MIGRATION.APP_MANIFEST).read_bytes(), own)
        self.assertIn(f"{MIGRATION.APP_MANIFEST}: unchanged", log)

    def test_crlf_is_kept(self) -> None:
        self.put(MIGRATION.APP_MANIFEST, APP_MANIFEST_BEFORE.replace("\n", "\r\n").encode("utf-8"))
        self.run_migration()
        raw = (self.repo / MIGRATION.APP_MANIFEST).read_bytes().decode("utf-8")
        self.assertNotIn("\n", raw.replace("\r\n", ""))
        self.assertTrue(raw.startswith(f"{EDITOR}{NEW}schema/"))

    def test_a_changed_passage_and_missing_files_are_left_alone(self) -> None:
        doc = self.repo / MIGRATION.USE_CASES_DOC
        doc.write_text("# Our own use cases\n", encoding="utf-8")
        (self.repo / MIGRATION.SCHEMA).unlink()
        (self.repo / MIGRATION.PROJECT_FILE).unlink()
        log = self.run_migration()
        self.assertEqual(doc.read_text(encoding="utf-8"), "# Our own use cases\n")
        self.assertIn("1 passage(s) differ from the template text and were left as they are", log)
        self.assertIn(f"{MIGRATION.SCHEMA}: not present in this repository", log)
        self.assertFalse((self.repo / MIGRATION.SCHEMA).exists() or (self.repo / MIGRATION.PROJECT_FILE).exists())

    def test_a_file_that_is_not_text_is_skipped(self) -> None:
        self.put(MIGRATION.INSTALL_DOC, b"\xff\xfe not utf-8")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.INSTALL_DOC}: SKIPPED", log)
        self.assertEqual((self.repo / MIGRATION.INSTALL_DOC).read_bytes(), b"\xff\xfe not utf-8")

    def test_the_sync_script_runs_the_migration_from_0_1_29(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.30", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.29", "--to-version", "0.1.30", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.30]", result.stdout)
        self.assertEqual((self.repo / MIGRATION.SCHEMA).read_bytes(), (ROOT / MIGRATION.SCHEMA).read_bytes())


if __name__ == "__main__":
    unittest.main()
