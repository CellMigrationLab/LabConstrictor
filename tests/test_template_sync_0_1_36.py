"""Tests of the 0.1.36 migration: the plugins are no longer called experimental, and use_cases.md (the "Examples" section) is removed."""
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

from _v0_1_36 import before_0_1_36, template_bytes
from _v0_1_37 import before_0_1_37


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_35_to_v0_1_36.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
DOCS = ROOT / ".tools/docs"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_36")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def at_0_1_36(relative: Path) -> bytes:
    """The 0.1.36 template file: the live file without the 0.1.37 change (tests/_v0_1_37.py)."""
    return before_0_1_37(relative, (ROOT / relative).read_bytes())


def old(relative: Path) -> bytes:
    """The 0.1.35 file: the live file without the 0.1.36 change (the frozen copy for a removed file)."""
    return before_0_1_36(relative, template_bytes(relative))


def user_pages() -> list[Path]:
    """The user-facing pages of .tools/docs (the migration_*.md design notes are history) and the README."""
    return [*sorted(path for path in DOCS.glob("*.md") if not path.name.startswith("migration_")), ROOT / "README.md"]


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(3[6-9]|[4-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_35_to_v0_1_36.py", text)

    def test_chains_from_older_versions_reach_0_1_36(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_36")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.16", "0.1.34", "0.1.35"):
            self.assertEqual(sync.resolve_migration_chain(manifest["migrations"], start, "0.1.36")[-1]["to"], "0.1.36", start)

    def test_the_design_note_exists_and_the_migration_links_it(self) -> None:
        self.assertTrue((DOCS / "migration_0_1_36.md").is_file())
        self.assertIn(".tools/docs/migration_0_1_36.md", MIGRATION.DOCS_URL)
        self.assertNotIn("migration_0_1_36.md", lf(DOCS / "README.md"), "the docs README does not list design notes")

    def test_the_removed_page_is_gone_and_its_frozen_copy_is_the_0_1_35_page(self) -> None:
        for relative in MIGRATION.REMOVED_FILES:
            with self.subTest(file=str(relative)):
                self.assertFalse((ROOT / relative).exists())
                self.assertIn("App Centre", lf(MIGRATION.PREVIOUS_ROOT / relative))

    def test_the_live_files_are_the_0_1_35_files_migrated(self) -> None:
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                text, applied, missing = MIGRATION.apply_edits(old(relative).decode("utf-8"), MIGRATION.EDITS[relative])
                self.assertEqual((applied, missing), (len(MIGRATION.EDITS[relative]), 0))
                self.assertEqual(text, at_0_1_36(relative).decode("utf-8"))

    def test_no_user_page_links_use_cases_or_calls_the_plugins_experimental(self) -> None:
        for path in user_pages():
            text = lf(path)
            with self.subTest(file=path.name):
                self.assertNotIn("use_cases.md", text)
                self.assertNotIn("## Examples", text)
                for line in text.splitlines():
                    if re.search(r"experimental|prototype", line, re.IGNORECASE):
                        # an app's maturity (`status: Experimental` of labconstrictor-app.yaml) is the app's own word, not the plugins'
                        self.assertIn("Experimental`", line)

    def test_the_relative_links_of_the_changed_pages_resolve(self) -> None:
        for relative in MIGRATION.EDITS:
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", at_0_1_36(relative).decode("utf-8")):
                if "://" in target:
                    continue
                with self.subTest(file=str(relative), target=target):
                    self.assertTrue(((ROOT / relative).parent / target).resolve().exists())


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_36_"))
        for relative in MIGRATION.FILES:
            self.put(relative, old(relative))

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
        for relative in MIGRATION.REMOVED_FILES:
            self.assertFalse((self.repo / relative).exists(), relative)
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes().replace(b"\r\n", b"\n"), at_0_1_36(relative))

    def test_an_app_of_0_1_35_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        log = self.run_migration()
        self.assert_template_state()
        self.assertIn(f"{MIGRATION.USE_CASES_DOC}: updated: removed", log)
        self.assertIn(f"done: {len(MIGRATION.FILES)} file(s) changed", log)
        self.assertNotIn("SKIPPED", log)
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertIn(f"{MIGRATION.USE_CASES_DOC}: not present in this repository (nothing was created)", again)
        self.assertNotIn("SKIPPED", again)

    def test_crlf_is_kept_and_a_crlf_copy_of_the_page_is_removed(self) -> None:
        for relative in MIGRATION.FILES:
            self.put(relative, old(relative).replace(b"\n", b"\r\n"))
        self.run_migration()
        self.assert_template_state()
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                self.assertNotIn(b"\n", (self.repo / relative).read_bytes().replace(b"\r\n", b""))

    def test_a_customised_use_cases_page_is_kept(self) -> None:
        page = self.put(MIGRATION.USE_CASES_DOC, old(MIGRATION.USE_CASES_DOC) + b"\n## Our own app\n")
        before = page.read_bytes()
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.USE_CASES_DOC}: SKIPPED: customised (not the 0.1.35 template file)", log)
        self.assertEqual(page.read_bytes(), before)

    def test_the_0_1_34_page_is_not_removed_by_this_step_alone(self) -> None:
        """An app at 0.1.34 reaches 0.1.36 through 0.1.35, which replaces the unchanged page first; on its own this step keeps it."""
        frozen = ROOT / ".template_sync/resources/v0_1_34_to_v0_1_35/previous" / MIGRATION.USE_CASES_DOC
        self.put(MIGRATION.USE_CASES_DOC, frozen.read_bytes())
        self.assertIn("SKIPPED", self.run_migration())
        self.assertTrue((self.repo / MIGRATION.USE_CASES_DOC).exists())

    def test_a_customised_passage_is_skipped_and_the_others_change(self) -> None:
        index = self.put(MIGRATION.DOCS_INDEX, b"# Our guides\n\nOur own text.\n")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.DOCS_INDEX}: SKIPPED: customised", log)
        self.assertEqual(index.read_bytes(), b"# Our guides\n\nOur own text.\n")
        text = old(MIGRATION.DOCS_INDEX).decode("utf-8").replace("- [LabConstrictor use cases](use_cases.md)\n", "- [Our examples](use_cases.md)\n")
        index.write_text(text, encoding="utf-8", newline="\n")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.DOCS_INDEX}: updated: 1 text change(s); SKIPPED 1 passage(s)", log)
        changed = lf(index)
        self.assertIn("- [Our examples](use_cases.md)\n", changed)
        self.assertIn("- [Expose tools to napari, Fiji and QuPath](tools_bridge.md)\n", changed)

    def test_missing_files_are_not_created(self) -> None:
        for relative in MIGRATION.FILES:
            (self.repo / relative).unlink()
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            self.assertIn(f"{relative}: not present in this repository (nothing was created)", log)
        self.assertEqual([p for p in self.repo.rglob("*") if p.is_file()], [])

    def test_a_file_that_is_not_text_is_skipped_and_kept(self) -> None:
        for relative in (MIGRATION.USE_CASES_DOC, MIGRATION.ROOT_README):
            self.put(relative, b"\xff\xfe not utf-8")
        log = self.run_migration()
        for relative in (MIGRATION.USE_CASES_DOC, MIGRATION.ROOT_README):
            with self.subTest(file=str(relative)):
                self.assertIn(f"{relative}: SKIPPED", log)
                self.assertEqual((self.repo / relative).read_bytes(), b"\xff\xfe not utf-8")

    def test_the_sync_script_runs_the_migration_from_0_1_35(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.36 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.36", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.35", "--to-version", "0.1.36", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.36]", result.stdout)
        self.assert_template_state()
        again = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertIn("no repository changes were required", again.stdout)

    def test_the_sync_chain_from_0_1_34_removes_an_unchanged_page(self) -> None:
        """0.1.35 replaces the 0.1.34 page with the App Centre page, then 0.1.36 removes it."""
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        frozen = ROOT / ".template_sync/resources/v0_1_34_to_v0_1_35/previous" / MIGRATION.USE_CASES_DOC
        self.put(MIGRATION.USE_CASES_DOC, frozen.read_bytes())
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.36", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.34", "--to-version", "0.1.36", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / MIGRATION.USE_CASES_DOC).exists(), result.stdout)


if __name__ == "__main__":
    unittest.main()
