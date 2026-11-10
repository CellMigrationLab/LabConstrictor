"""Tests of the 0.1.21 migration: the constructor environment pins conda-standalone>=26.9.3 (no admin prompt at uninstall on Windows)."""
from __future__ import annotations

import importlib.util
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
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_20_to_v0_1_21.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
BASH = shutil.which("bash")


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_21")
CREATE_ENV = MIGRATION.CREATE_ENV


def live_text() -> str:
    return (ROOT / CREATE_ENV).read_text(encoding="utf-8")


def old_text() -> str:
    """The 0.1.20 script: the live file with the 0.1.21 block put back to the 0.1.20 line."""
    return live_text().replace(MIGRATION.CREATE_NEW, MIGRATION.CREATE_OLD)


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.21", text)
        self.assertIn("script: migrations/v0_1_20_to_v0_1_21.py", text)

    def test_chains_from_every_older_version_reach_0_1_21(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_21")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.15", "0.1.18", "0.1.19", "0.1.20"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.21")
            self.assertEqual(chain[-1]["to"], "0.1.21", start)

    def test_the_design_note_and_troubleshooting_entry_are_linked(self) -> None:
        self.assertIn("(migration_0_1_21.md)", (ROOT / ".tools/docs/README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_21.md").is_file())
        self.assertIn("(migration_0_1_21.md)", (ROOT / ".tools/docs/troubleshooting_installed_app.md").read_text(encoding="utf-8"))

    def test_the_live_script_holds_the_new_block_once_and_pins_26_9_3(self) -> None:
        text = live_text()
        self.assertEqual(text.count(MIGRATION.CREATE_NEW), 1)
        self.assertNotIn(MIGRATION.CREATE_OLD, text)
        self.assertIn('constructor "conda-standalone>=26.9.3"', text)
        self.assertNotIn("\r\n", (ROOT / CREATE_ENV).read_bytes().decode("utf-8"))

    def test_the_0_1_20_line_differs_from_the_new_one_only_by_the_pin(self) -> None:
        new_command = MIGRATION.CREATE_NEW.splitlines()[-1]
        self.assertEqual(new_command, MIGRATION.CREATE_OLD.rstrip("\n") + ' "conda-standalone>=26.9.3"')

    @unittest.skipUnless(BASH, "bash is not available")
    def test_the_live_script_is_valid_shell(self) -> None:
        result = subprocess.run([BASH or "bash", "-n", str(ROOT / CREATE_ENV)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, text: str, newline: str = "\n") -> Path:
        path = self.repo / CREATE_ENV
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return path

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_a_0_1_20_app_gets_the_pin_and_a_second_run_changes_nothing(self) -> None:
        path = self.put(old_text())
        output = self.run_migration()
        self.assertIn(f"{CREATE_ENV}: updated: conda-standalone>=26.9.3", output)
        self.assertEqual(path.read_text(encoding="utf-8"), live_text())
        before = path.read_bytes()
        again = self.run_migration()
        self.assertIn(f"{CREATE_ENV}: unchanged: already pins conda-standalone>=26.9.3", again)
        self.assertIn("no repository changes were required", again)
        self.assertEqual(path.read_bytes(), before)

    def test_crlf_files_keep_their_line_endings(self) -> None:
        path = self.put(old_text(), newline="\r\n")
        self.assertIn(f"{CREATE_ENV}: updated", self.run_migration())
        data = path.read_bytes()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertEqual(data.decode("utf-8").replace("\r\n", "\n"), live_text())

    def test_a_script_that_already_names_conda_standalone_is_skipped(self) -> None:
        custom = old_text().replace("python=3.11 constructor\n", 'python=3.11 constructor "conda-standalone>=26.10"\n')
        path = self.put(custom)
        output = self.run_migration()
        self.assertIn(f"{CREATE_ENV}: SKIPPED: the file already names conda-standalone", output)
        self.assertEqual(path.read_text(encoding="utf-8"), custom)

    def test_a_customised_script_is_skipped_and_left_as_it_is(self) -> None:
        custom = old_text().replace("python=3.11 constructor\n", "python=3.12 constructor\n")
        path = self.put(custom)
        output = self.run_migration()
        self.assertIn(f"{CREATE_ENV}: SKIPPED: the 0.1.20 conda create line was not found", output)
        self.assertEqual(path.read_text(encoding="utf-8"), custom)

    def test_a_missing_file_is_not_created(self) -> None:
        output = self.run_migration()
        self.assertIn(f"{CREATE_ENV}: SKIPPED, file not found", output)
        self.assertFalse((self.repo / CREATE_ENV).exists())

    @unittest.skipUnless(BASH, "bash is not available")
    def test_the_migrated_script_is_valid_shell(self) -> None:
        path = self.put(old_text())
        self.run_migration()
        result = subprocess.run([BASH or "bash", "-n", str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_20(self) -> None:
        path = self.put(old_text())
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        sync = str(self.repo / ".template_sync/sync.py")
        command = [sys.executable, sync, "--from-version", "0.1.20", "--to-version", "0.1.21", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.21]", result.stdout)
        self.assertEqual(path.read_text(encoding="utf-8"), live_text())
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
