"""Tests of the 0.1.34 migration: the Tools pin moves from v0.3.0-alpha.3 to v0.3.0-alpha.4 (Fiji opens results as hyperstacks, Tools #165)."""
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


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_33_to_v0_1_34.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_34")
SH, BAT = MIGRATION.POST_INSTALL_SH, MIGRATION.POST_INSTALL_BAT
OLD, NEW = MIGRATION.OLD_PIN, MIGRATION.NEW_PIN


def live(relative: Path) -> bytes:
    """The live template file (0.1.34 is the newest migration)."""
    return (ROOT / relative).read_bytes()


class TemplateTests(unittest.TestCase):
    def test_the_template_pins_the_new_tag_once_per_script(self) -> None:
        for relative in (SH, BAT):
            text = live(relative).decode("utf-8")
            with self.subTest(file=str(relative)):
                self.assertEqual(text.count(NEW), 1)
                self.assertNotIn(OLD, text)
        self.assertIn("\r\n", (ROOT / BAT).read_bytes().decode("utf-8"), "post_install.bat stays CRLF")

    def test_the_manifest_lists_the_migration_and_the_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.34", text)  # the newest migration: update when a later one is added
        self.assertIn("script: migrations/v0_1_33_to_v0_1_34.py", text)
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_34.md").is_file())


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_34_"))
        for relative in (SH, BAT):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(live(relative).replace(NEW.encode(), OLD.encode()))

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()

    def test_an_app_of_0_1_33_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        log = self.run_migration()
        for relative in (SH, BAT):
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), live(relative))
        self.assertEqual(log.count(f"updated: Tools pin {OLD} -> {NEW}"), 2, log)
        self.assertIn("2 change(s)", log)
        self.assertIn("no repository changes were required", self.run_migration())

    def test_an_own_pin_is_left_alone(self) -> None:
        sh = self.repo / SH
        sh.write_bytes(sh.read_bytes().replace(OLD.encode(), b"v0.2.0-rc.2"))
        before = sh.read_bytes()
        log = self.run_migration()
        self.assertEqual(sh.read_bytes(), before)
        self.assertIn("has its own pin v0.2.0-rc.2: left as it is", log)

    def test_a_script_without_the_hook_or_files_missing_are_left_alone(self) -> None:
        (self.repo / SH).write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
        (self.repo / BAT).unlink()
        log = self.run_migration()
        self.assertIn("has no Tools bridge hook", log)
        self.assertIn(f"{BAT}: not present in this repository", log)
        self.assertFalse((self.repo / BAT).exists())

    def test_the_sync_script_runs_the_migration_from_0_1_33(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.34", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.33", "--to-version", "0.1.34", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.34]", result.stdout)
        self.assertEqual((self.repo / SH).read_bytes(), live(SH))


if __name__ == "__main__":
    unittest.main()
