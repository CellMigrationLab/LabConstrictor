"""Tests of the 0.1.19 migration: src_change.yaml in every installer (bump_constructor.py), Python series in setup.py (merge_requirements.py)."""
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
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_18_to_v0_1_19.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
BUMP = Path(".tools/python/bump_constructor.py")
MERGE = Path(".tools/python/merge_requirements.py")


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_19")


def old_text(relative: Path) -> str:
    """The 0.1.18 version of a template script: the live file with the 0.1.19 block put back to the 0.1.18 block."""
    new, old = (MIGRATION.BUMP_NEW, MIGRATION.BUMP_OLD) if relative == BUMP else (MIGRATION.MERGE_NEW, MIGRATION.MERGE_OLD)
    return (ROOT / relative).read_text(encoding="utf-8").replace(new, old)


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.19", text)
        self.assertIn("script: migrations/v0_1_18_to_v0_1_19.py", text)

    def test_chains_from_every_older_version_reach_0_1_19(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_19")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.15", "0.1.17", "0.1.18"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.19")
            self.assertEqual(chain[-1]["to"], "0.1.19", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_19.md)", (ROOT / ".tools/docs/README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_19.md").is_file())

    def test_the_live_template_scripts_hold_the_new_blocks_once(self) -> None:
        for relative, old, new in ((BUMP, MIGRATION.BUMP_OLD, MIGRATION.BUMP_NEW), (MERGE, MIGRATION.MERGE_OLD, MIGRATION.MERGE_NEW)):
            with self.subTest(file=str(relative)):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertEqual(text.count(new), 1)
                self.assertEqual(text.count(old), 0)


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".tools/python").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path | str, text: str, newline: str = "\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return path

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_a_0_1_18_app_gets_both_fixes_and_a_second_run_changes_nothing(self) -> None:
        bump = self.put(BUMP, old_text(BUMP))
        merge = self.put(MERGE, old_text(MERGE))
        setup = self.put("setup.py", 'setup(\n    name="demo",\n    python_requires=">=3.12.13",\n)\n')
        output = self.run_migration()
        self.assertIn(f"{BUMP}: updated", output)
        self.assertIn(f"{MERGE}: updated", output)
        self.assertIn("setup.py: updated: python_requires >=3.12", output)
        self.assertEqual(bump.read_text(encoding="utf-8"), (ROOT / BUMP).read_text(encoding="utf-8"))
        self.assertEqual(merge.read_text(encoding="utf-8"), (ROOT / MERGE).read_text(encoding="utf-8"))
        self.assertIn('python_requires=">=3.12",', setup.read_text(encoding="utf-8"))
        before = {p: p.read_bytes() for p in (bump, merge, setup)}
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertEqual({p: p.read_bytes() for p in (bump, merge, setup)}, before)

    def test_an_app_that_already_has_the_fixes_is_unchanged(self) -> None:
        """CellTracksColab took both fixes before this template version (its pull requests 66 and 67)."""
        self.put(BUMP, (ROOT / BUMP).read_text(encoding="utf-8"))
        self.put(MERGE, (ROOT / MERGE).read_text(encoding="utf-8"))
        self.put("setup.py", 'python_requires=">=3.12",\n')
        output = self.run_migration()
        self.assertIn(f"{BUMP}: unchanged: already has the 0.1.19 block", output)
        self.assertIn(f"{MERGE}: unchanged: already has the 0.1.19 block", output)
        self.assertIn("setup.py: unchanged: python_requires already names a Python series", output)

    def test_crlf_files_keep_their_line_endings(self) -> None:
        bump = self.put(BUMP, old_text(BUMP), newline="\r\n")
        self.assertIn(f"{BUMP}: updated", self.run_migration())
        data = bump.read_bytes()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertEqual(data.decode("utf-8").replace("\r\n", "\n"), (ROOT / BUMP).read_text(encoding="utf-8"))

    def test_a_customised_script_is_skipped_and_left_as_it_is(self) -> None:
        custom = old_text(BUMP).replace("src change marker mapping already present", "our own message")
        bump = self.put(BUMP, custom)
        output = self.run_migration()
        self.assertIn(f"{BUMP}: SKIPPED: the 0.1.18 block was not found", output)
        self.assertEqual(bump.read_text(encoding="utf-8"), custom)

    def test_missing_files_are_not_created(self) -> None:
        output = self.run_migration()
        for relative in (BUMP, MERGE, Path("setup.py")):
            self.assertIn(f"{relative}: SKIPPED, file not found", output)
            self.assertFalse((self.repo / relative).exists())

    def test_setup_py_shapes(self) -> None:
        cases = {
            'python_requires=">=3.11.13"': ('python_requires=">=3.11"', "updated"),
            "python_requires='>=3.12.13'": ("python_requires='>=3.12'", "updated"),
            'python_requires=">=PYTHON_VERSION"': ('python_requires=">=PYTHON_VERSION"', "unchanged"),
            'python_requires=">=3.12"': ('python_requires=">=3.12"', "unchanged"),
            'python_requires="~=3.12.1"': ('python_requires="~=3.12.1"', "unchanged"),
        }
        for before, (after, status) in cases.items():
            with self.subTest(setup=before):
                setup = self.put("setup.py", f"setup({before})\n")
                output = self.run_migration()
                self.assertIn(f"setup.py: {status}", output)
                self.assertEqual(setup.read_text(encoding="utf-8"), f"setup({after})\n")


class FixedScriptTests(unittest.TestCase):
    """Run the template scripts themselves on a small app, as the release and notebook workflows do."""

    def make_app(self, root: Path, bump_text: str) -> None:
        (root / ".tools/python").mkdir(parents=True)
        (root / ".tools/meta").mkdir(parents=True)
        (root / ".tools/meta/src_change.yaml").write_text('src_last_modified: "2026-10-22_00:00:00"\n', encoding="utf-8")
        (root / ".tools/python/bump_constructor.py").write_text(bump_text, encoding="utf-8")
        (root / "src/demo").mkdir(parents=True)
        (root / "src/demo/__init__.py").write_text("", encoding="utf-8")
        (root / "src/demo/core.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "notebooks/Demo").mkdir(parents=True)
        (root / "notebooks/Demo/Demo.ipynb").write_text("{}", encoding="utf-8")
        (root / "setup.py").write_text('from setuptools import setup\nsetup(name="demo", python_requires=">=3.12")\n', encoding="utf-8")
        (root / "construct.yaml").write_text(
            "name: Demo\nversion: 0.0.1\nextra_files:\n"
            "- app/menuinst/Welcome.ipynb: Demo/notebooks/Welcome.ipynb\n"
            "- .tools/meta/src_change.yaml: Demo/src_change.yaml\n",
            encoding="utf-8",
        )

    def src_change_entries_after_three_runs(self, bump_text: str) -> list[int]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_app(root, bump_text)
            counts = []
            for _ in range(3):
                result = subprocess.run([sys.executable, ".tools/python/bump_constructor.py"], cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                counts.append((root / "construct.yaml").read_text(encoding="utf-8").count(".tools/meta/src_change.yaml"))
            return counts

    def test_the_fixed_bump_constructor_keeps_src_change_yaml_in_every_release(self) -> None:
        self.assertEqual(self.src_change_entries_after_three_runs((ROOT / BUMP).read_text(encoding="utf-8")), [1, 1, 1])

    def test_the_0_1_18_bump_constructor_dropped_it_every_other_release(self) -> None:
        self.assertEqual(self.src_change_entries_after_three_runs(old_text(BUMP)), [0, 1, 0])

    def test_merge_requirements_writes_the_python_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(ROOT / MERGE, root / "merge_requirements.py")
            (root / "notebooks/Demo").mkdir(parents=True)
            (root / "notebooks/Demo/requirements.yaml").write_text("python_version: 3.12.13\ndependencies:\n- numpy==2.0.2\n", encoding="utf-8")
            (root / "environment.yaml").write_text("name: demo\ndependencies:\n- python=3.11.0\n- jupyterlab=4.4.0\n", encoding="utf-8")
            (root / "setup.py").write_text('from setuptools import setup\nsetup(name="demo", python_requires=">=PYTHON_VERSION")\n', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "merge_requirements.py", "--source-dir", "notebooks", "--output", "requirements.txt"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('python_requires=">=3.12"', (root / "setup.py").read_text(encoding="utf-8"))
            self.assertIn("python=3.12.13", (root / "environment.yaml").read_text(encoding="utf-8"))


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_18(self) -> None:
        self.put(BUMP, old_text(BUMP))
        self.put(MERGE, old_text(MERGE))
        self.put("setup.py", 'python_requires=">=3.12.13"\n')
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"  # sync.py checks the target against the manifest: stop the chain at 0.1.19
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.19", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.18", "--to-version", "0.1.19", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.19]", result.stdout)
        self.assertEqual((self.repo / BUMP).read_text(encoding="utf-8"), (ROOT / BUMP).read_text(encoding="utf-8"))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
