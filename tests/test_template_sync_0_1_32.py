"""Tests of the 0.1.32 migration: the user docs link to the guide that owns a topic (plugin install steps, writing tools)."""
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

from _v0_1_32 import before_0_1_32


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_31_to_v0_1_32.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
DOCS = ROOT / ".tools/docs"
SITE = "https://cellmigrationlab.github.io/LabConstrictor-Site/"
AUTHORING = "https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/AUTHORING.md"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_32")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def old(relative: Path) -> bytes:
    """The 0.1.31 file: the live file without the 0.1.32 change."""
    return before_0_1_32(relative, (ROOT / relative).read_bytes())


def user_pages() -> list[Path]:
    """The user-facing pages of .tools/docs (the migration_*.md design notes are history)."""
    return sorted(path for path in DOCS.glob("*.md") if not path.name.startswith("migration_"))


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(3[2-9]|[4-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_31_to_v0_1_32.py", text)

    def test_chains_from_older_versions_reach_0_1_32(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_32")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.16", "0.1.24", "0.1.31"):
            self.assertEqual(sync.resolve_migration_chain(manifest["migrations"], start, "0.1.32")[-1]["to"], "0.1.32", start)

    def test_the_design_note_exists_and_the_migration_links_it(self) -> None:
        self.assertTrue((DOCS / "migration_0_1_32.md").is_file())
        self.assertIn(".tools/docs/migration_0_1_32.md", MIGRATION.DOCS_URL)
        self.assertNotIn("migration_0_1_32.md", lf(DOCS / "README.md"), "the docs README does not list design notes")

    def test_the_resources_are_the_live_guide_and_the_0_1_31_one(self) -> None:
        for relative in MIGRATION.WHOLE_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((MIGRATION.RESOURCE_ROOT / relative).read_bytes(), (ROOT / relative).read_bytes())
                self.assertNotEqual(lf(MIGRATION.PREVIOUS_ROOT / relative), lf(ROOT / relative))

    def test_the_live_files_are_the_0_1_31_files_migrated(self) -> None:
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                text, applied, missing = MIGRATION.apply_edits(old(relative).decode("utf-8"), MIGRATION.EDITS[relative])
                self.assertEqual((applied, missing), (len(MIGRATION.EDITS[relative]), 0))
                self.assertEqual(text, lf(ROOT / relative))

    def test_the_tools_guide_links_the_owner_guides(self) -> None:
        text = lf(ROOT / MIGRATION.TOOLS_DOC)
        for address in (f"{SITE}guides/image-software/", f"{SITE}guides/napari/", f"{SITE}guides/fiji/", f"{SITE}guides/qupath/", AUTHORING):
            with self.subTest(address=address):
                self.assertIn(f"]({address})", text)
        self.assertIn(f"]({SITE}guides/image-software/)", lf(ROOT / MIGRATION.INSTALL_DOC))

    def test_no_user_page_repeats_the_plugin_install_steps_or_a_version_pin(self) -> None:
        pin = re.search(r'LC_TOOLS_PIN="([^"]+)"', lf(ROOT / "app/bash_bat_scripts/post_install.sh"))
        assert pin is not None
        repeated = (
            pin.group(1),                                   # the Tools pin: set in the scripts only
            "LabConstrictor-Tools/archive/refs/tags/",      # the address the pin builds
            "pip install napari-labconstrictor",            # napari plugin install step
            "labconstrictor-fiji.jar",                      # Fiji plugin install step
            "update site",                                  # Fiji install situation
            "Extension Manager",                            # QuPath install step
            "for the install steps",                        # the old pointer to the plugin READMEs
        )
        for path in [*user_pages(), ROOT / "README.md"]:
            text = lf(path)
            for needle in repeated:
                with self.subTest(file=path.name, text=needle):
                    self.assertNotIn(needle, text)

    def test_the_pin_is_still_set_in_both_scripts(self) -> None:
        self.assertRegex(lf(ROOT / "app/bash_bat_scripts/post_install.sh"), r'\n\s*LC_TOOLS_PIN="v[^"]+"\n')
        self.assertRegex(lf(ROOT / "app/bash_bat_scripts/post_install.bat"), r'\nSET "LC_TOOLS_PIN=v[^"]+"\n')

    def test_the_relative_links_of_the_changed_pages_resolve(self) -> None:
        for relative in MIGRATION.FILES:
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", lf(ROOT / relative)):
                if "://" in target:
                    continue
                with self.subTest(file=str(relative), target=target):
                    self.assertTrue(((ROOT / relative).parent / target).resolve().exists())


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_32_"))
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

    def test_an_app_of_0_1_31_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        for relative in MIGRATION.FILES:
            self.assertNotEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes(), relative)
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), (ROOT / relative).read_bytes())
        self.assertIn(f"done: {len(MIGRATION.FILES)} file(s) changed", log)
        self.assertNotIn("SKIPPED", log)
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertNotIn("SKIPPED", again)

    def test_crlf_is_kept(self) -> None:
        for relative in MIGRATION.FILES:
            self.put(relative, old(relative).replace(b"\n", b"\r\n"))
        self.run_migration()
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                raw = (self.repo / relative).read_bytes()
                self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
                self.assertEqual(raw.replace(b"\r\n", b"\n"), (ROOT / relative).read_bytes())

    def test_a_customised_guide_is_skipped(self) -> None:
        guide = self.put(MIGRATION.TOOLS_DOC, old(MIGRATION.TOOLS_DOC) + b"\nOur own note.\n")
        before = guide.read_bytes()
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.TOOLS_DOC}: SKIPPED: customised (not the 0.1.31 template file)", log)
        self.assertEqual(guide.read_bytes(), before)

    def test_a_customised_passage_is_skipped_and_the_others_change(self) -> None:
        install = self.put(MIGRATION.INSTALL_DOC, b"# Install our app\n\nOur own text.\n")
        text = old(MIGRATION.INSTALL_DOC).decode("utf-8").replace("is listed in Napari, and not in Fiji", "is listed in Napari only, not in Fiji")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.INSTALL_DOC}: SKIPPED: customised", log)
        self.assertEqual(install.read_bytes(), b"# Install our app\n\nOur own text.\n")
        install.write_text(text, encoding="utf-8", newline="\n")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.INSTALL_DOC}: updated: 2 text change(s); SKIPPED 1 passage(s)", log)
        changed = lf(install)
        self.assertIn("is listed in Napari only, not in Fiji", changed)
        self.assertIn(f"]({SITE}guides/image-software/)", changed)
        self.assertIn(f"{MIGRATION.INSTALL_DOC}: unchanged: the other changes are there; SKIPPED 1 passage(s)", self.run_migration())

    def test_missing_files_are_not_created(self) -> None:
        for relative in MIGRATION.FILES:
            (self.repo / relative).unlink()
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            self.assertIn(f"{relative}: not present in this repository (nothing was created)", log)
        self.assertEqual([p for p in self.repo.rglob("*") if p.is_file()], [])

    def test_a_file_that_is_not_text_is_skipped(self) -> None:
        self.put(MIGRATION.TOOLS_DOC, b"\xff\xfe not utf-8")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.TOOLS_DOC}: SKIPPED", log)
        self.assertEqual((self.repo / MIGRATION.TOOLS_DOC).read_bytes(), b"\xff\xfe not utf-8")

    def test_the_sync_script_runs_the_migration_from_0_1_31(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.32 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.32", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.31", "--to-version", "0.1.32", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.32]", result.stdout)
        self.assertEqual((self.repo / MIGRATION.TOOLS_DOC).read_bytes(), (ROOT / MIGRATION.TOOLS_DOC).read_bytes())
        again = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
