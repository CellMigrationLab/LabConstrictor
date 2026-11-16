"""Tests of the 0.1.30 migration: requirements that disagree stop the merge (#48); the notebook update asks and keeps a backup (#49)."""
from __future__ import annotations

import ast
import importlib.util
import json
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
from typing import Any, Callable
from unittest import mock

from _v0_1_30 import WELCOME_0_1_29, before_0_1_30


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_29_to_v0_1_30.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
MERGE_PATH = ROOT / ".tools/python/merge_requirements.py"
ENVIRONMENT = "name: app\nchannels:\n- conda-forge\ndependencies:\n- python=3.11.13\n- pip\n- jupyterlab=4.4.0\n"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_30")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def old(relative: Path) -> str:
    """The 0.1.29 file: the live file without the 0.1.30 change."""
    return before_0_1_30(relative, (ROOT / relative).read_bytes()).decode("utf-8").replace("\r\n", "\n")


def helpers() -> ModuleType:
    return MIGRATION._load("v0_1_9_to_v0_1_10.py", "helpers_for_0_1_30_tests")


def table_cell(notebook: Path) -> str:
    cells = json.loads(lf(notebook))["cells"]
    return next("".join(c["source"]) for c in cells if c["cell_type"] == "code" and "def apply_grid_layout(" in "".join(c["source"]))


def backup_function() -> Callable[[Path, str], Path | None]:
    """replace_notebook_with_backup of the live Welcome template, run on its own."""
    tree = ast.parse(table_cell(ROOT / MIGRATION.WELCOME_TEMPLATE).replace("DICT_OF_NOTEBOOKS", "{}"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "replace_notebook_with_backup")
    scope: dict[str, Any] = {"json": json, "shutil": shutil, "Path": Path}
    exec(compile(ast.Module([function], []), "replace_notebook_with_backup", "exec"), scope)  # noqa: S102 - the template's own function
    return scope["replace_notebook_with_backup"]


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = lf(ROOT / ".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.([3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_29_to_v0_1_30.py", text)

    def test_chains_from_every_older_version_reach_0_1_30(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_30")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.16", "0.1.24", "0.1.29"):
            self.assertEqual(sync.resolve_migration_chain(manifest["migrations"], start, "0.1.30")[-1]["to"], "0.1.30", start)

    def test_the_design_note_exists_and_the_migration_links_it(self) -> None:
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_30.md").is_file())
        self.assertIn(".tools/docs/migration_0_1_30.md", MIGRATION.DOCS_URL)

    def test_the_resources_are_the_live_merge_script_and_the_0_1_29_one(self) -> None:
        self.assertEqual((MIGRATION.RESOURCE_ROOT / MIGRATION.MERGE).read_bytes(), MERGE_PATH.read_bytes())
        self.assertNotEqual(lf(MIGRATION.PREVIOUS_ROOT / MIGRATION.MERGE), lf(MERGE_PATH))
        self.assertIn('"--check"', lf(MERGE_PATH))

    def test_the_live_files_are_the_0_1_29_files_migrated(self) -> None:
        self.assertEqual(MIGRATION.apply_blocks(old(MIGRATION.NOTEBOOK_WORKFLOW), MIGRATION.NOTEBOOK_WORKFLOW_BLOCKS), lf(ROOT / MIGRATION.NOTEBOOK_WORKFLOW))
        self.assertEqual(MIGRATION.add_requirements_check(old(MIGRATION.RELEASE_WORKFLOW)), lf(ROOT / MIGRATION.RELEASE_WORKFLOW))
        self.assertEqual(old(MIGRATION.TOOLS_REQUIREMENTS) + MIGRATION.PACKAGING_LINES, lf(ROOT / MIGRATION.TOOLS_REQUIREMENTS))
        with tempfile.TemporaryDirectory() as tmp:
            welcome = Path(tmp) / "Welcome_template.ipynb"
            shutil.copy(WELCOME_0_1_29, welcome)
            self.assertTrue(MIGRATION._update_welcome(helpers(), welcome).startswith("updated"))
            self.assertEqual(welcome.read_bytes(), (ROOT / MIGRATION.WELCOME_TEMPLATE).read_bytes())

    def test_the_release_checks_the_requirements_in_the_bump_version_job_before_the_commit(self) -> None:
        text = lf(ROOT / MIGRATION.RELEASE_WORKFLOW)
        check = text.index("merge_requirements.py --source-dir notebooks --output requirements.txt --check")
        self.assertLess(text.index("python .tools/python/check_placeholders.py"), check)
        self.assertLess(check, text.index("Commit updated versioned files"))
        self.assertEqual(text.count("--output requirements.txt --check"), 1)

    def test_the_tools_install_packaging(self) -> None:
        self.assertIn(MIGRATION.PACKAGING_PIN, lf(ROOT / MIGRATION.TOOLS_REQUIREMENTS).splitlines())


class MergeCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "environment.yaml").write_text(ENVIRONMENT, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def notebook(self, name: str, *dependencies: str, **os_lists: list[str]) -> None:
        folder = self.root / "notebooks" / name
        folder.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {"dependencies": list(dependencies), "python_version": "3.11.13", **os_lists}
        (folder / "requirements.yaml").write_text(json.dumps(data), encoding="utf-8")  # JSON is YAML

    def overrides(self, text: str) -> None:
        (self.root / "requirements_overrides.yaml").write_text(text, encoding="utf-8")

    def merge(self, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-W", "ignore", str(MERGE_PATH), "--source-dir", "notebooks", "--output", "requirements.txt", *extra]
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True)

    def lines(self, name: str = "requirements.txt") -> list[str]:
        return [line for line in lf(self.root / name).splitlines() if line and not line.startswith("#")]

    def assert_conflict(self, result: subprocess.CompletedProcess[str], *expected: str) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for text in expected:
            self.assertIn(text, result.stderr)
        self.assertFalse((self.root / "requirements.txt").exists(), "nothing is written when requirements conflict")


class MergeRequirementsTests(MergeCase):
    def test_different_exact_pins_stop_the_merge_in_either_file_order(self) -> None:
        for first, second in (("A", "B"), ("B", "A")):
            with self.subTest(order=first + second):
                shutil.rmtree(self.root / "notebooks", ignore_errors=True)
                self.notebook(first, "numpy==1.26.4")
                self.notebook(second, "numpy==2.0.0")
                self.assert_conflict(self.merge(), "numpy: pinned to different versions (1.26.4, 2.0.0)",
                                     f"notebooks/{first}/requirements.yaml: numpy==1.26.4", f"notebooks/{second}/requirements.yaml: numpy==2.0.0",
                                     "requirements_overrides.yaml")

    def test_identical_pins_and_spellings_of_one_package_merge_into_one_line(self) -> None:
        self.notebook("A", "NumPy==1.26.4", "scikit_image==0.25.2")
        self.notebook("B", "numpy==1.26.4", "scikit-image==0.25.2")
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self.lines()
        self.assertIn("NumPy==1.26.4", lines)
        self.assertIn("scikit_image==0.25.2", lines)
        self.assertEqual(sum(line.lower().startswith(("numpy", "scikit")) for line in lines), 2)

    def test_requirements_that_are_not_pins_are_kept_as_written_and_combined(self) -> None:
        self.notebook("A", "numpy<2.0", "pandas>=2.0,<3")
        self.notebook("B", "numpy>=1.24")
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn("numpy<2.0,>=1.24", self.lines())
        self.assertIn("pandas<3,>=2.0", self.lines())

    def test_a_pin_inside_the_other_ranges_is_used(self) -> None:
        self.notebook("A", "numpy>=1.24,<2")
        self.notebook("B", "numpy==1.26.4")
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn("numpy==1.26.4", self.lines())

    def test_a_pin_outside_another_range_and_ranges_no_version_meets_stop_the_merge(self) -> None:
        self.notebook("A", "numpy<2")
        self.notebook("B", "numpy==2.0.0")
        self.assert_conflict(self.merge(), "the pin ==2.0.0 does not meet numpy<2 of notebooks/A/requirements.yaml")
        self.notebook("B", "numpy>=2.1")
        self.assert_conflict(self.merge(), "numpy: no version meets all of these requirements")

    def test_requirements_for_different_platforms_stay_separate_lines(self) -> None:
        self.notebook("A", 'numpy==1.26.4 ; sys_platform == "win32"')
        self.notebook("B", 'numpy==2.0.0 ; sys_platform != "win32"')
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn('numpy==1.26.4 ; sys_platform == "win32"', self.lines())
        self.assertIn('numpy==2.0.0 ; sys_platform != "win32"', self.lines())

    def test_extras_are_combined(self) -> None:
        self.notebook("A", "dask[array]==2024.8.0")
        self.notebook("B", "dask[dataframe]==2024.8.0")
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn("dask[array,dataframe]==2024.8.0", self.lines())

    def test_an_os_specific_pin_is_checked_against_the_common_one(self) -> None:
        self.notebook("A", "numpy==1.26.4", linux_dependencies=["numpy==2.0.0"])
        self.assert_conflict(self.merge(), "numpy (linux_dependencies, with the common dependencies): pinned to different versions")
        self.notebook("A", "numpy==1.26.4", linux_dependencies=["numpy>=1.20"])
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn("numpy>=1.20", self.lines("requirements-linux.txt"))

    def test_an_override_decides_and_is_written_with_its_reason_in_every_file(self) -> None:
        self.notebook("A", "numpy==1.26.4", "tensorflow==2.20.0")
        self.notebook("B", "numpy==2.0.0")
        self.overrides('overrides:\n  NumPy:\n    use: "==2.0.0"\n    reason: "A was re-run with 2.0.0: same results."\n')
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("numpy==2.0.0", self.lines())
        for name in ("requirements.txt", "requirements_gpu.txt"):
            header = [line for line in lf(self.root / name).splitlines() if line.startswith("# Decided")]
            self.assertEqual(len(header), 1, name)
            self.assertIn("notebooks/A/requirements.yaml: numpy==1.26.4", header[0])
            self.assertIn("Reason: A was re-run with 2.0.0: same results.", header[0])

    def test_an_override_needs_a_reason_and_a_version_requirement(self) -> None:
        self.notebook("A", "numpy==1.26.4")
        self.overrides('overrides:\n  numpy:\n    use: "==2.0.0"\n')
        self.assert_conflict(self.merge(), "numpy needs `reason`")
        self.overrides('overrides:\n  numpy:\n    use: "2.0.0"\n    reason: "x"\n')
        self.assert_conflict(self.merge(), "is not a version requirement")

    def test_an_override_no_notebook_uses_is_reported(self) -> None:
        self.notebook("A", "numpy==1.26.4")
        self.overrides('overrides:\n  torch:\n    use: "==2.9.0"\n    reason: "old"\n')
        result = self.merge()
        self.assertEqual(result.returncode, 0)
        self.assertIn("decides torch, which no notebook requires any more", result.stdout)

    def test_check_writes_nothing_and_fails_on_a_conflict(self) -> None:
        self.notebook("A", "numpy==1.26.4")
        self.notebook("B", "numpy==1.26.4")
        result = self.merge("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["environment.yaml", "notebooks"])
        self.assertEqual(lf(self.root / "environment.yaml"), ENVIRONMENT)
        self.notebook("B", "numpy==2.0.0")
        self.assert_conflict(self.merge("--check"), "pinned to different versions")

    def test_the_app_packages_are_still_added(self) -> None:
        self.notebook("A", "numpy==1.26.4")
        self.assertEqual(self.merge().returncode, 0)
        self.assertIn("jl-hidecode==0.0.1", self.lines())
        self.assertIn("ipywidgets==8.1.7", self.lines())


class SatisfiableTests(unittest.TestCase):
    def test_ranges(self) -> None:
        from packaging.specifiers import SpecifierSet

        merge = load(MERGE_PATH, "merge_requirements_0_1_30")
        for spec, expected in (("<2,>=2.1", False), (">=1.24,<2", True), (">1.0,<1.1", True), ("~=1.11.0,<1.11", False),
                               ("==1.*,>=1.5", True), ("==1.*,>=2", False), ("!=1.0", True), ("", True)):
            with self.subTest(spec=spec):
                self.assertEqual(merge.satisfiable(SpecifierSet(spec)), expected)


class NotebookBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.notebook = Path(self._tmp.name) / "Folder" / "Analysis.ipynb"
        self.replace = backup_function()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def files(self) -> list[str]:
        return sorted(p.name for p in self.notebook.parent.iterdir())

    def test_a_first_install_needs_no_backup(self) -> None:
        self.assertIsNone(self.replace(self.notebook, '{"cells": []}'))
        self.assertEqual(self.files(), ["Analysis.ipynb"])

    def test_the_user_copy_with_changes_and_outputs_is_kept(self) -> None:
        mine = '{"cells": [{"source": "my parameter", "outputs": ["my result"]}]}'
        self.notebook.parent.mkdir(parents=True)
        self.notebook.write_text(mine, encoding="utf-8")
        backup = self.replace(self.notebook, '{"cells": ["new"]}')
        assert backup is not None
        self.assertRegex(backup.name, r"^Analysis\.backup-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.ipynb$")
        self.assertEqual(backup.read_text(encoding="utf-8"), mine)
        self.assertEqual(self.notebook.read_text(encoding="utf-8"), '{"cells": ["new"]}')
        second = self.replace(self.notebook, '{"cells": ["newer"]}')
        assert second is not None
        self.assertNotEqual(second, backup, "an earlier backup is never overwritten")
        self.assertEqual(second.read_text(encoding="utf-8"), '{"cells": ["new"]}')
        self.assertEqual(len(self.files()), 3)

    def test_a_download_that_is_not_a_notebook_changes_nothing(self) -> None:
        self.notebook.parent.mkdir(parents=True)
        self.notebook.write_text('{"cells": ["mine"]}', encoding="utf-8")
        for content in ("<html>rate limit</html>", "[]"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.replace(self.notebook, content)
        self.assertEqual(self.notebook.read_text(encoding="utf-8"), '{"cells": ["mine"]}')
        self.assertEqual(self.files(), ["Analysis.ipynb"])

    def test_a_failed_write_keeps_the_notebook_and_leaves_no_temporary_file(self) -> None:
        self.notebook.parent.mkdir(parents=True)
        self.notebook.write_text('{"cells": ["mine"]}', encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
            self.replace(self.notebook, '{"cells": ["new"]}')
        self.assertEqual(self.notebook.read_text(encoding="utf-8"), '{"cells": ["mine"]}')
        self.assertFalse(any(name.endswith(".update") for name in self.files()))

    def test_the_handler_asks_first_and_records_the_version_after_the_replacement(self) -> None:
        cell = table_cell(ROOT / MIGRATION.WELCOME_TEMPLATE)
        handler = cell[cell.index("def button_update(") :]
        self.assertNotIn("local_notebook_path.write_text", cell)
        replace = handler.index("backup_path = replace_notebook_with_backup(local_notebook_path, notebook_content)")
        self.assertLess(replace, handler.index("local_latest_versions[main_folder][subfolder] = new_version"))
        self.assertLess(handler.index('widgets.Button(description="Back up and update"'), handler.index("return show"))
        self.assertIn("confirm.on_click(", handler)
        self.assertIn("nothing was changed", handler)
        compile(cell.replace("DICT_OF_NOTEBOOKS", "{}"), "Welcome table cell", "exec")


class MigrationCase(unittest.TestCase):
    NUCLEISKY_LIKE = {
        "App": ["torch==2.10.0", "tifffile==2026.4.11", "numpy==2.0.2", "scikit-image==0.26.0"],
        "Benchmark": ["torch==2.9.0", "tifffile==2026.1.28", "numpy==2.0.2", "scikit-image==0.25.2"],
    }

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path | str, text: str, newline: str = "\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return path

    def put_0_1_29_app(self, notebooks: dict[str, list[str]] | None = None, newline: str = "\n") -> None:
        self.put(MIGRATION.MERGE, lf(MIGRATION.PREVIOUS_ROOT / MIGRATION.MERGE), newline)
        for relative in (MIGRATION.TOOLS_REQUIREMENTS, MIGRATION.NOTEBOOK_WORKFLOW, MIGRATION.RELEASE_WORKFLOW):
            self.put(relative, old(relative), newline)
        self.put(MIGRATION.WELCOME_TEMPLATE, lf(WELCOME_0_1_29), newline)
        self.put("environment.yaml", ENVIRONMENT)
        for name, dependencies in (notebooks or {}).items():
            self.put(f"notebooks/{name}/requirements.yaml", "python_version: 3.11.13\ndependencies:\n" + "".join(f"- {d}\n" for d in dependencies))

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()

    def merge(self, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-W", "ignore", str(self.repo / MIGRATION.MERGE), "--source-dir", "notebooks", "--output", "requirements.txt", *extra]
        return subprocess.run(command, cwd=self.repo, capture_output=True, text=True)


class MigrationBehaviourTests(MigrationCase):
    def test_a_0_1_29_app_reaches_the_0_1_30_files_and_a_second_run_changes_nothing(self) -> None:
        self.put_0_1_29_app()
        output = self.run_migration()
        for relative in (MIGRATION.MERGE, MIGRATION.TOOLS_REQUIREMENTS, MIGRATION.NOTEBOOK_WORKFLOW, MIGRATION.RELEASE_WORKFLOW, MIGRATION.WELCOME_TEMPLATE):
            with self.subTest(file=str(relative)):
                self.assertRegex(output, rf"{re.escape(str(relative))}: updated")
                self.assertEqual(lf(self.repo / relative), lf(ROOT / relative))
        self.assertIn(f"{MIGRATION.OVERRIDES}: not needed", output)
        self.assertNotIn("SKIPPED", output)
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertEqual({p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}, before)

    def test_pins_that_disagree_are_recorded_and_the_app_keeps_its_versions(self) -> None:
        self.put_0_1_29_app(self.NUCLEISKY_LIKE)
        before = subprocess.run([sys.executable, "-W", "ignore", str(MIGRATION.PREVIOUS_ROOT / MIGRATION.MERGE), "--source-dir", "notebooks",
                                 "--output", "before.txt"], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(before.returncode, 0, before.stderr)
        new_merge = subprocess.run([sys.executable, "-W", "ignore", str(MERGE_PATH), "--source-dir", "notebooks", "--output", "requirements.txt", "--check"],
                                   cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(new_merge.returncode, 1, "the 0.1.29 notebooks conflict for the new merge")
        output = self.run_migration()
        self.assertIn("requirements_overrides.yaml: updated: created; it records the version used until now for scikit-image, tifffile, torch", output)
        decisions = lf(self.repo / MIGRATION.OVERRIDES)
        self.assertIn('  torch:\n    use: "==2.10.0"\n', decisions)
        self.assertIn('  scikit-image:\n    use: "==0.26.0"\n', decisions)
        self.assertIn("notebooks/App/requirements.yaml ==2.10.0, notebooks/Benchmark/requirements.yaml ==2.9.0", decisions)
        self.assertNotIn("numpy", decisions)
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        pins = {line.split("==")[0].lower().replace("_", "-"): line.split("==")[1] for line in lf(self.repo / "requirements.txt").splitlines() if "==" in line and not line.startswith("#")}
        old_pins = {line.split("==")[0].lower().replace("_", "-"): line.split("==")[1] for line in lf(self.repo / "before.txt").splitlines() if "==" in line and not line.startswith("#")}
        self.assertEqual(pins, old_pins, "the recorded decisions give the versions the 0.1.29 merge gave")
        self.assertEqual(lf(self.repo / "requirements.txt").count("# Decided in requirements_overrides.yaml"), 3)

    def test_spellings_of_one_package_are_one_decision(self) -> None:
        self.put_0_1_29_app({"A": ["scikit-image==0.26.0"], "B": ["scikit_image==0.25.2"], "C": ["Scikit.Image==0.25.2"]})
        self.run_migration()
        decisions = lf(self.repo / MIGRATION.OVERRIDES)
        self.assertEqual(decisions.count("  scikit-image:\n"), 1)
        self.assertIn('use: "==0.26.0"', decisions)
        self.assertEqual(self.merge().returncode, 0)

    def test_without_yaml_the_simple_list_forms_are_read(self) -> None:
        text = "python_version: 3.11.1\ndependencies: \n - ipywidgets==8.1.2  # widgets\n - 'pyyaml==6.0.2'\ndescription: \"x\"\nlinux_dependencies: []\n"
        with mock.patch.dict(sys.modules, {"yaml": None}):
            self.assertEqual(MIGRATION.notebook_dependencies(text), ["ipywidgets==8.1.2", "pyyaml==6.0.2"])
            self.assertEqual(MIGRATION.notebook_dependencies("dependencies: [numpy==1.0, 'scipy==1.1']\n"), ["numpy==1.0", "scipy==1.1"])

    def test_crlf_files_keep_their_line_endings(self) -> None:
        self.put_0_1_29_app(newline="\r\n")
        self.run_migration()
        for relative in (MIGRATION.MERGE, MIGRATION.TOOLS_REQUIREMENTS, MIGRATION.NOTEBOOK_WORKFLOW, MIGRATION.RELEASE_WORKFLOW):
            with self.subTest(file=str(relative)):
                data = (self.repo / relative).read_bytes()
                self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
                self.assertEqual(data.decode("utf-8").replace("\r\n", "\n"), lf(ROOT / relative))

    def test_a_customised_merge_script_is_kept_and_the_release_does_not_call_check(self) -> None:
        self.put_0_1_29_app(self.NUCLEISKY_LIKE)
        custom = self.put(MIGRATION.MERGE, lf(MIGRATION.PREVIOUS_ROOT / MIGRATION.MERGE) + "# my change\n")
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.MERGE}: SKIPPED: customised", output)
        self.assertIn(f"{MIGRATION.RELEASE_WORKFLOW}: SKIPPED: the repository's merge_requirements.py has no --check", output)
        self.assertTrue(lf(custom).endswith("# my change\n"))
        self.assertNotIn("--check", lf(self.repo / MIGRATION.RELEASE_WORKFLOW))
        self.assertTrue((self.repo / MIGRATION.OVERRIDES).is_file())

    def test_an_existing_overrides_file_and_customised_files_are_left_as_they_are(self) -> None:
        self.put_0_1_29_app(self.NUCLEISKY_LIKE)
        mine = self.put(MIGRATION.OVERRIDES, "overrides: {}\n")
        welcome = self.repo / MIGRATION.WELCOME_TEMPLATE
        welcome.write_text(lf(welcome).replace("def button_update(main_folder, subfolder, row_idx):", "def my_update(main_folder, subfolder, row_idx):"), encoding="utf-8")
        workflow = self.put(MIGRATION.NOTEBOOK_WORKFLOW, "name: mine\n")
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.OVERRIDES}: already exists: unchanged", output)
        self.assertIn(f"{MIGRATION.WELCOME_TEMPLATE}: SKIPPED", output)
        self.assertIn(f"{MIGRATION.NOTEBOOK_WORKFLOW}: SKIPPED", output)
        self.assertEqual(lf(mine), "overrides: {}\n")
        self.assertEqual(lf(workflow), "name: mine\n")
        self.assertIn("def my_update(", lf(welcome))

    def test_missing_files_are_not_created(self) -> None:
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.MERGE}: not present", output)
        self.assertIn(f"{MIGRATION.OVERRIDES}: not needed", output)
        self.assertEqual(list(self.repo.rglob("*")), [])


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_29(self) -> None:
        self.put_0_1_29_app(self.NUCLEISKY_LIKE)
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        # sync.py refuses a target other than the manifest version: pin the copy to 0.1.30 (later templates add migrations).
        manifest = self.repo / ".template_sync/manifest.yaml"
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.30", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.29", "--to-version", "0.1.30", "--repository-root", str(self.repo)]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.30]", result.stdout)
        self.assertEqual(lf(self.repo / MIGRATION.MERGE), lf(MERGE_PATH))
        self.assertEqual(self.merge("--check").returncode, 0)
        again = subprocess.run(command, capture_output=True, text=True, env=env)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
