"""Tests of the 0.1.35 migration: user docs fixed after a review of the website (uninstall steps, links to the website's guides, App Centre,
heading style)."""
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

from _v0_1_35 import before_0_1_35
from _v0_1_36 import before_0_1_36, template_bytes


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_34_to_v0_1_35.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
DOCS = ROOT / ".tools/docs"
SITE = "https://cellmigrationlab.github.io/LabConstrictor-Site/"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_35")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def live(relative: Path) -> bytes:
    """The template file as 0.1.35 left it (later changes undone, tests/_v0_1_36.py and newer; a file removed later is its frozen copy)."""
    return before_0_1_36(relative, template_bytes(relative))


def old(relative: Path) -> bytes:
    """The 0.1.34 file: the live file without the 0.1.35 change."""
    return before_0_1_35(relative, template_bytes(relative))


def user_pages() -> list[Path]:
    """The user-facing pages of .tools/docs (the migration_*.md design notes are history)."""
    return sorted(path for path in DOCS.glob("*.md") if not path.name.startswith("migration_"))


def slug(title: str) -> str:
    """The anchor GitHub and the website give a heading (lower case, punctuation dropped, spaces to hyphens)."""
    return re.sub(r"[^\w\- ]", "", title.strip().lower()).replace(" ", "-")


class TemplateTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(3[5-9]|[4-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_34_to_v0_1_35.py", text)

    def test_chains_from_older_versions_reach_0_1_35(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_35")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.16", "0.1.31", "0.1.34"):
            self.assertEqual(sync.resolve_migration_chain(manifest["migrations"], start, "0.1.35")[-1]["to"], "0.1.35", start)

    def test_the_design_note_exists_and_the_migration_links_it(self) -> None:
        self.assertTrue((DOCS / "migration_0_1_35.md").is_file())
        self.assertIn(".tools/docs/migration_0_1_35.md", MIGRATION.DOCS_URL)
        self.assertNotIn("migration_0_1_35.md", lf(DOCS / "README.md"), "the docs README does not list design notes")

    def test_the_resources_are_the_live_page_and_the_0_1_34_one(self) -> None:
        for relative in MIGRATION.WHOLE_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((MIGRATION.RESOURCE_ROOT / relative).read_bytes(), live(relative))
                self.assertNotEqual(lf(MIGRATION.PREVIOUS_ROOT / relative), live(relative).decode("utf-8"))

    def test_the_live_files_are_the_0_1_34_files_migrated(self) -> None:
        for relative in MIGRATION.EDITS:
            with self.subTest(file=str(relative)):
                text, applied, missing = MIGRATION.apply_edits(old(relative).decode("utf-8"), MIGRATION.EDITS[relative])
                self.assertEqual((applied, missing), (len(MIGRATION.EDITS[relative]), 0))
                self.assertEqual(text, live(relative).decode("utf-8"))

    def test_install_says_how_to_uninstall_on_each_system(self) -> None:
        text = lf(ROOT / MIGRATION.INSTALL_DOC)
        self.assertEqual(text.count("\n## Uninstall an app\n"), 1)
        section = text.split("\n## Uninstall an app\n", 1)[1].split("\n## ", 1)[0]
        for needle in ("Settings > Apps > Installed apps", "`Uninstall-<AppName>.exe`", "uninstall.sh", "macOS", "Linux"):
            with self.subTest(text=needle):
                self.assertIn(needle, section)
        self.assertIn("[uninstalling the old version](#uninstall-an-app)", text)

    def test_the_names_in_the_uninstall_steps_are_those_the_installer_creates(self) -> None:
        construct = lf(ROOT / "construct.yaml")
        self.assertIn("app/bash_bat_scripts/uninstall.sh: uninstall.sh", construct, "uninstall.sh is shipped in the install folder")
        bat = lf(ROOT / "app/bash_bat_scripts/post_install.bat")
        self.assertIn('SET "UNINSTALL_EXE=%PREFIX%\\Uninstall-UNDERSCORED_PROJECT_NAME.exe"', bat)
        self.assertIn("HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\", bat, "the app is in the Installed apps list")

    def test_no_user_page_links_to_the_download_stub_for_uninstalling_or_to_authoring_on_github(self) -> None:
        for path in user_pages():
            text = lf(path)
            with self.subTest(file=path.name):
                self.assertNotIn("[uninstalling guide](./download_executable.md)", text)
                self.assertNotIn(MIGRATION.AUTHORING_ON_GITHUB, text)
        self.assertEqual(live(MIGRATION.TOOLS_DOC).decode("utf-8").count(f"]({MIGRATION.WRITING_TOOLS})"), 2)
        self.assertIn("](install.md#uninstall-an-app)", lf(ROOT / MIGRATION.TROUBLESHOOTING_DOC))

    def test_use_cases_links_to_the_app_centre(self) -> None:
        text = live(MIGRATION.USE_CASES_DOC).decode("utf-8")
        self.assertIn(f"]({SITE}apps/)", text)
        self.assertNotIn("## VLab4Mic", text)

    def test_user_page_headings_follow_the_website_style(self) -> None:
        emoji = re.compile("[☀-➿\U0001f300-\U0001faff]")
        for relative in MIGRATION.EDITS:
            for line in lf(ROOT / relative).splitlines():
                if not line.startswith("#"):
                    continue
                with self.subTest(file=relative.name, heading=line):
                    self.assertIsNone(emoji.search(line))
                    self.assertFalse(line.endswith(":"))

    def test_the_links_of_the_changed_pages_resolve(self) -> None:
        for relative in MIGRATION.FILES:
            for target, anchor in re.findall(r"\]\(([^)#\s]*)(?:#([^)\s]*))?\)", live(relative).decode("utf-8")):
                if "://" in target:
                    continue
                with self.subTest(file=str(relative), target=target, anchor=anchor):
                    page = ((ROOT / relative).parent / target).resolve() if target else ROOT / relative
                    self.assertTrue(page.exists())
                    if anchor:
                        headings = [slug(line.lstrip("#")) for line in lf(page).splitlines() if line.startswith("#")]
                        self.assertIn(anchor, headings)


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="lc_0_1_35_"))
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

    def test_an_app_of_0_1_34_gets_the_template_files_and_a_second_run_changes_nothing(self) -> None:
        for relative in MIGRATION.FILES:
            self.assertNotEqual((self.repo / relative).read_bytes(), live(relative), relative)
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), live(relative))
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
                self.assertEqual(raw.replace(b"\r\n", b"\n"), live(relative))

    def test_a_customised_use_cases_page_is_skipped(self) -> None:
        page = self.put(MIGRATION.USE_CASES_DOC, old(MIGRATION.USE_CASES_DOC) + b"\n## Our own app\n")
        before = page.read_bytes()
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.USE_CASES_DOC}: SKIPPED: customised (not the 0.1.34 template file)", log)
        self.assertEqual(page.read_bytes(), before)

    def test_a_customised_passage_is_skipped_and_the_others_change(self) -> None:
        relative = Path(".tools/docs/installer_images.md")
        page = self.put(relative, b"# Our images\n\nOur own text.\n")
        log = self.run_migration()
        self.assertIn(f"{relative}: SKIPPED: customised", log)
        self.assertEqual(page.read_bytes(), b"# Our images\n\nOur own text.\n")
        page.write_text(old(relative).decode("utf-8").replace("## Logo:\n", "## Our logo:\n"), encoding="utf-8", newline="\n")
        log = self.run_migration()
        self.assertIn(f"{relative}: updated: 4 text change(s); SKIPPED 1 passage(s)", log)
        changed = lf(page)
        self.assertIn("\n## Our logo:\n", changed)
        self.assertIn("\n## Default installer\n", changed)
        self.assertIn(f"{relative}: unchanged: the other changes are there; SKIPPED 1 passage(s)", self.run_migration())

    def test_missing_files_are_not_created(self) -> None:
        for relative in MIGRATION.FILES:
            (self.repo / relative).unlink()
        log = self.run_migration()
        for relative in MIGRATION.FILES:
            self.assertIn(f"{relative}: not present in this repository (nothing was created)", log)
        self.assertEqual([p for p in self.repo.rglob("*") if p.is_file()], [])

    def test_a_file_that_is_not_text_is_skipped(self) -> None:
        self.put(MIGRATION.INSTALL_DOC, b"\xff\xfe not utf-8")
        log = self.run_migration()
        self.assertIn(f"{MIGRATION.INSTALL_DOC}: SKIPPED", log)
        self.assertEqual((self.repo / MIGRATION.INSTALL_DOC).read_bytes(), b"\xff\xfe not utf-8")

    def test_the_sync_script_runs_the_migration_from_0_1_34(self) -> None:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.35 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.35", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.34", "--to-version", "0.1.35", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.35]", result.stdout)
        for relative in MIGRATION.FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual((self.repo / relative).read_bytes(), live(relative))
        again = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
