"""Tests of the 0.1.26 migration: the app's own documentation explains PyPI publishing (added in 0.1.25)."""
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
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_25_to_v0_1_26.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_26")
PAGE = MIGRATION.EXTERNAL_CODE_PAGE
TROUBLESHOOTING = MIGRATION.TROUBLESHOOTING_PAGE
SECTION = MIGRATION.resource(MIGRATION.PYPI_SECTION)
ENTRY = MIGRATION.resource(MIGRATION.PYPI_TROUBLESHOOTING)


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def links(text_lf: str) -> str:
    """The Previous / Home / Next links of a page (the last ones)."""
    return list(MIGRATION.FOOTER.finditer(text_lf))[-1].group(0)


def without(relative: Path, heading: str) -> str:
    """A live page without the section that starts at the heading (it runs to the page's links)."""
    live = lf(ROOT / relative)
    start = live.index(heading)
    footer = list(MIGRATION.FOOTER.finditer(live))[-1].start()
    return live[:start].rstrip("\n") + "\n\n" + live[footer:]


def page_0_1_24() -> str:
    """The template's external_code_upload.md before 0.1.25: the live page without its PyPI section."""
    return without(PAGE, MIGRATION.SECTION_HEADING)


def troubleshooting_0_1_24() -> str:
    """The template's troubleshooting.md of 0.1.24: its links were in the middle, the entries of 0.1.23 and 0.1.24 after them."""
    page = without(TROUBLESHOOTING, MIGRATION.TROUBLESHOOTING_HEADING)
    footer = links(page)
    content = page.replace(footer, "").rstrip("\n")
    first_late_entry = content.index('## The release stops at "check_placeholders.py"')
    return content[:first_late_entry].rstrip("\n") + "\n\n" + footer + "\n" + content[first_late_entry:] + "\n"


# The page as the apps have it (the Playground, CellTracksColab, ...): another title and other Previous / Next links.
APP_PAGE = page_0_1_24().replace("# Upload external code\n", "# Adding External Code\n", 1).replace(
    "[← Previous](app_manifest.md)", "[← Previous](initialise_repository.md)"
)
APP_TROUBLESHOOTING = """# Troubleshooting

## App still appears in the Windows Installed apps list after uninstalling

Restart the computer.
"""


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(2[6-9]|[3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_25_to_v0_1_26.py", text)

    def test_chains_from_every_older_version_reach_0_1_26(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_26")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.19", "0.1.24", "0.1.25"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.26")
            self.assertEqual(chain[-1]["to"], "0.1.26", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_26.md)", lf(ROOT / ".tools/docs/README.md"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_26.md").is_file())

    def test_the_migration_turns_the_0_1_24_pages_into_the_live_pages(self) -> None:
        # The frozen texts are exactly the template's sections, at the place the template has them.
        self.assertEqual(MIGRATION.add_section(page_0_1_24(), SECTION), lf(ROOT / PAGE))
        old = troubleshooting_0_1_24()
        self.assertFalse(old.endswith(links(old)))  # the links were in the middle
        self.assertEqual(MIGRATION.add_section(old, ENTRY), lf(ROOT / TROUBLESHOOTING))

    def test_every_documentation_page_ends_with_its_links(self) -> None:
        for path in sorted((ROOT / ".tools/docs").glob("*.md")):
            text = lf(path)
            found = list(MIGRATION.FOOTER.finditer(text))
            if found:
                with self.subTest(page=path.name):
                    self.assertEqual(len(found), 1)
                    self.assertEqual(text[found[0].end():].strip(), "")

    def test_the_added_texts_work_in_an_app(self) -> None:
        for name, text in (("section", SECTION), ("entry", ENTRY)):
            with self.subTest(text=name):
                # no placeholder: the form does not fill in the documentation of an app
                self.assertNotRegex(text, r"PYTHON_PROJ_NAME|PYTHON_VERSION|VERSION_NUMBER")
                self.assertNotIn("\r", text)
                # the relative links name pages that every app has; the design notes are not in the apps
                for target in re.findall(r"\]\(([^)#]+)", text):
                    if target.startswith("http"):
                        continue
                    self.assertNotIn("migration_", target)
                    self.assertTrue((ROOT / ".tools/docs" / target).is_file(), target)
                    self.assertIn(target, ("external_code_upload.md", "troubleshooting.md", "executable_creation.md"))

    def test_the_section_starts_with_its_heading(self) -> None:
        self.assertTrue(SECTION.startswith(MIGRATION.SECTION_HEADING + "\n"))
        self.assertTrue(ENTRY.startswith(MIGRATION.TROUBLESHOOTING_HEADING + "\n"))


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".tools/docs").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path, text: str, newline: str = "\n") -> None:
        (self.repo / relative).write_bytes(text.replace("\n", newline).encode("utf-8"))

    def read(self, relative: Path) -> bytes:
        return (self.repo / relative).read_bytes()

    def run_migration(self) -> str:
        out = StringIO()
        with redirect_stdout(out):
            MIGRATION.migrate(self.repo, {})
        return out.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_the_template_pages_of_0_1_25_become_the_live_pages_and_a_second_run_changes_nothing(self) -> None:
        self.put(PAGE, page_0_1_24())
        self.put(TROUBLESHOOTING, troubleshooting_0_1_24())
        log = self.run_migration()
        self.assertEqual(lf(self.repo / PAGE), lf(ROOT / PAGE))
        self.assertEqual(lf(self.repo / TROUBLESHOOTING), lf(ROOT / TROUBLESHOOTING))
        self.assertIn("2 file(s) changed", log)
        self.assertIn("no repository changes were required", self.run_migration())

    def test_an_app_page_gets_the_section_before_its_links_and_keeps_crlf(self) -> None:
        self.put(PAGE, APP_PAGE, "\r\n")
        self.put(TROUBLESHOOTING, APP_TROUBLESHOOTING, "\r\n")
        self.run_migration()
        page = self.read(PAGE).decode("utf-8")
        self.assertNotIn("\n", page.replace("\r\n", ""))
        text = page.replace("\r\n", "\n")
        self.assertTrue(text.startswith("# Adding External Code\n"))
        self.assertIn("\n\n" + SECTION + "\n---\n\n<div align=\"center\">", text)
        self.assertIn("[← Previous](initialise_repository.md)", text)
        self.assertEqual(text.count(MIGRATION.SECTION_HEADING), 1)
        self.assertLess(text.index("## 3. How to import"), text.index(MIGRATION.SECTION_HEADING))
        trouble = self.read(TROUBLESHOOTING).decode("utf-8")
        self.assertNotIn("\n", trouble.replace("\r\n", ""))
        self.assertEqual(trouble.replace("\r\n", "\n"), APP_TROUBLESHOOTING + "\n" + ENTRY)
        before = (self.read(PAGE), self.read(TROUBLESHOOTING))
        self.assertIn("no repository changes were required", self.run_migration())
        self.assertEqual((self.read(PAGE), self.read(TROUBLESHOOTING)), before)

    def test_a_troubleshooting_page_with_links_gets_the_entry_before_them(self) -> None:
        footer = links(APP_PAGE)
        self.put(TROUBLESHOOTING, APP_TROUBLESHOOTING + "\n" + footer)
        self.run_migration()
        self.assertEqual(lf(self.repo / TROUBLESHOOTING), APP_TROUBLESHOOTING + "\n" + ENTRY + "\n" + footer)

    def test_links_in_the_middle_of_a_page_are_moved_to_its_bottom(self) -> None:
        footer = links(APP_PAGE)
        self.put(TROUBLESHOOTING, APP_TROUBLESHOOTING + "\n" + footer + "\n## Added later\n\nText.\n")
        self.run_migration()
        expected = APP_TROUBLESHOOTING + "\n## Added later\n\nText.\n\n" + ENTRY + "\n" + footer
        self.assertEqual(lf(self.repo / TROUBLESHOOTING), expected)

    def test_a_page_without_links_gets_the_section_at_its_end(self) -> None:
        self.put(PAGE, "# Adding External Code\n\n## 3. How to import into your notebook\n\nimport it\n\n\n")
        self.run_migration()
        self.assertEqual(lf(self.repo / PAGE), "# Adding External Code\n\n## 3. How to import into your notebook\n\nimport it\n\n" + SECTION)

    def test_a_page_with_a_section_4_of_its_own_is_left_as_it_is(self) -> None:
        own = APP_PAGE.replace("---\n\n<div", "## 4. Use it in Colab\n\nOur own text.\n\n---\n\n<div", 1)
        self.put(PAGE, own)
        log = self.run_migration()
        self.assertEqual(lf(self.repo / PAGE), own)
        self.assertIn(f"{PAGE}: SKIPPED: the page has a section 4 of its own", log)

    def test_pages_that_already_explain_it_are_unchanged(self) -> None:
        # The template itself (or an app that copied the texts by hand).
        for relative in (PAGE, TROUBLESHOOTING):
            shutil.copyfile(ROOT / relative, self.repo / relative)
        before = (self.read(PAGE), self.read(TROUBLESHOOTING))
        log = self.run_migration()
        self.assertEqual((self.read(PAGE), self.read(TROUBLESHOOTING)), before)
        self.assertIn("unchanged: already explains PyPI publishing", log)
        self.assertIn("unchanged: already has the entry Publishing to PyPI fails", log)

    def test_missing_pages_are_not_created(self) -> None:
        log = self.run_migration()
        self.assertFalse((self.repo / PAGE).exists())
        self.assertFalse((self.repo / TROUBLESHOOTING).exists())
        self.assertIn(f"{PAGE}: not present in this repository", log)
        self.assertIn("no repository changes were required", log)

    def test_an_unreadable_page_is_skipped_without_failing(self) -> None:
        (self.repo / PAGE).write_bytes(b"\xff\xfe not utf-8")
        self.put(TROUBLESHOOTING, APP_TROUBLESHOOTING)
        log = self.run_migration()
        self.assertIn(f"{PAGE}: SKIPPED", log)
        self.assertEqual(self.read(PAGE), b"\xff\xfe not utf-8")
        self.assertIn("1 file(s) changed", log)


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_25(self) -> None:
        self.put(PAGE, APP_PAGE)
        self.put(TROUBLESHOOTING, APP_TROUBLESHOOTING)
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.26 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.26", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.25", "--to-version", "0.1.26", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.26]", result.stdout)
        self.assertIn(SECTION, lf(self.repo / PAGE))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
