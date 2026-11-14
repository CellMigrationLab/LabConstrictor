"""Tests of the 0.1.27 migration: the schema copy accepts host_requirements and app_manifest.md documents it (Tools #155)."""
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


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_26_to_v0_1_27.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_27")
SCHEMA = MIGRATION.SCHEMA
PAGE = MIGRATION.MANIFEST_PAGE
SECTION_TEXT = (MIGRATION.RESOURCE_ROOT / MIGRATION.SECTION).read_text(encoding="utf-8")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def page_before() -> str:
    """The template's page of 0.1.26: the live page without the new section."""
    live = lf(ROOT / PAGE)
    return live.replace(SECTION_TEXT + "\n", "", 1)


class ResourceTests(unittest.TestCase):
    def test_the_resources_are_the_template_files(self) -> None:
        self.assertEqual((MIGRATION.RESOURCE_ROOT / SCHEMA).read_bytes(), (ROOT / SCHEMA).read_bytes())
        self.assertIn(SECTION_TEXT, lf(ROOT / PAGE))
        self.assertNotIn("PROJECT_NAME", SECTION_TEXT)

    def test_the_schema_accepts_and_checks_host_requirements(self) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads((ROOT / SCHEMA).read_text(encoding="utf-8"))
        base = {"schema": 1, "name": "StarDist2D", "summary": "Segment nuclei with StarDist in 2D images.", "kind": "segmentation",
                "distribution": {"installer": True}}
        good = dict(base, host_requirements={"qupath": {"min_version": "0.1.0-alpha.6", "features": ["shapes_owner_v1"]}})
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(good)), [])
        bads: list[dict[str, dict[str, object]]] = [{"notebook": {"min_version": "1"}}, {"fiji": {}}, {"fiji": {"min_version": "latest"}}, {"fiji": {"min_version": "1", "x": 1}}]
        for bad in bads:
            with self.subTest(bad):
                self.assertTrue(list(Draft202012Validator(schema).iter_errors(dict(base, host_requirements=bad))))


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_27_"))
        (self.repo / ".tools/docs").mkdir(parents=True)
        (self.repo / ".tools/schema").mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()


class MigrationTests(MigrationCase):
    def test_an_app_of_0_1_26_gets_the_template_files(self) -> None:
        (self.repo / SCHEMA).write_text('{"old": true}\n', encoding="utf-8")
        (self.repo / PAGE).write_text(page_before(), encoding="utf-8")
        log = self.run_migration()
        self.assertEqual((self.repo / SCHEMA).read_bytes(), (ROOT / SCHEMA).read_bytes())
        self.assertEqual(lf(self.repo / PAGE), lf(ROOT / PAGE))
        self.assertIn("2 file(s) changed", log)
        self.assertIn("no repository changes were required", self.run_migration())

    def test_crlf_is_kept_and_a_page_without_the_anchor_gets_it_before_its_links(self) -> None:
        page = "# Describe your app\n\nOur text.\n\n---\n\n<div align=\"center\">\n\n[Home](README.md)\n\n</div>\n"
        (self.repo / PAGE).write_bytes(page.replace("\n", "\r\n").encode("utf-8"))
        self.run_migration()
        raw = (self.repo / PAGE).read_bytes().decode("utf-8")
        self.assertNotIn("\n", raw.replace("\r\n", ""))
        text = raw.replace("\r\n", "\n")
        self.assertLess(text.index(MIGRATION.SECTION_HEADING), text.index('<div align="center">'))
        self.assertTrue(text.startswith("# Describe your app\n\nOur text.\n\n"))

    def test_a_page_without_anchor_or_links_gets_it_at_the_end(self) -> None:
        (self.repo / PAGE).write_text("# Ours\n", encoding="utf-8")
        self.run_migration()
        self.assertTrue(lf(self.repo / PAGE).rstrip().endswith(SECTION_TEXT.rstrip()))

    def test_missing_files_are_not_created_and_bad_ones_are_skipped(self) -> None:
        log = self.run_migration()
        self.assertFalse((self.repo / SCHEMA).exists() or (self.repo / PAGE).exists())
        self.assertIn("no repository changes were required", log)
        (self.repo / PAGE).write_bytes(b"\xff\xfe not utf-8")
        log = self.run_migration()
        self.assertIn(f"{PAGE}: SKIPPED", log)
        self.assertEqual((self.repo / PAGE).read_bytes(), b"\xff\xfe not utf-8")


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_26(self) -> None:
        (self.repo / SCHEMA).write_text('{"old": true}\n', encoding="utf-8")
        (self.repo / PAGE).write_text(page_before(), encoding="utf-8")
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.27", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.26", "--to-version", "0.1.27", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.27]", result.stdout)
        self.assertEqual((self.repo / SCHEMA).read_bytes(), (ROOT / SCHEMA).read_bytes())


if __name__ == "__main__":
    unittest.main()
