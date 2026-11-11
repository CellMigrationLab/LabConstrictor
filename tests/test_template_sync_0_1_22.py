"""Tests of the 0.1.22 migration: tensorflow[and-cuda] only on Linux in the GPU file; the version cell reads the grouped version file."""
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
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_21_to_v0_1_22.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_22")
MERGE_MODULE = load(ROOT / ".tools/python/merge_requirements.py", "merge_requirements_0_1_22")
MERGE = MIGRATION.MERGE
UPLOAD_DOC = MIGRATION.UPLOAD_DOC


def live(relative: Path) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def old_merge() -> str:
    """The 0.1.21 merge_requirements.py: the live file with the three 0.1.22 blocks put back."""
    text = live(MERGE).replace(MIGRATION.MERGE_FUNCTION, "", 1)
    text = text.replace(MIGRATION.MERGE_BODY_NEW, MIGRATION.MERGE_BODY_OLD, 1)
    return text.replace(MIGRATION.MERGE_DOC_NEW, MIGRATION.MERGE_DOC_OLD, 1)


def old_upload() -> str:
    return live(UPLOAD_DOC).replace(MIGRATION.UPLOAD_NEW, MIGRATION.UPLOAD_OLD, 1)


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = live(Path(".template_sync/manifest.yaml"))
        self.assertRegex(text, r"template_version: 0\.1\.(2[2-9]|[3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_21_to_v0_1_22.py", text)

    def test_chains_from_every_older_version_reach_0_1_22(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_22")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.15", "0.1.20", "0.1.21"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.22")
            self.assertEqual(chain[-1]["to"], "0.1.22", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_22.md)", live(Path(".tools/docs/README.md")))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_22.md").is_file())

    def test_the_live_files_hold_each_new_block_once(self) -> None:
        merge = live(MERGE)
        self.assertEqual(merge.count(MIGRATION.MERGE_FUNCTION), 1)
        self.assertEqual(merge.count(MIGRATION.MERGE_BODY_NEW), 1)
        self.assertEqual(merge.count(MIGRATION.MERGE_DOC_NEW), 1)
        self.assertNotIn(MIGRATION.MERGE_BODY_OLD, merge)
        self.assertEqual(live(UPLOAD_DOC).count(MIGRATION.UPLOAD_NEW), 1)
        self.assertNotIn(MIGRATION.UPLOAD_OLD, live(UPLOAD_DOC))


class GpuLinesTests(unittest.TestCase):
    def test_a_pinned_tensorflow_gets_cuda_on_linux_only(self) -> None:
        self.assertEqual(
            MERGE_MODULE.build_gpu_lines(["numpy==2.1.3", "tensorflow==2.20.0"]),
            ["numpy==2.1.3", 'tensorflow[and-cuda]==2.20.0 ; sys_platform == "linux"', 'tensorflow==2.20.0 ; sys_platform != "linux"'],
        )

    def test_extras_and_markers_are_kept(self) -> None:
        lines = MERGE_MODULE.tensorflow_gpu_lines('tensorflow[foo]>=2.16 ; python_version >= "3.10"')
        self.assertEqual(
            lines,
            [
                'tensorflow[foo,and-cuda]>=2.16 ; (python_version >= "3.10") and sys_platform == "linux"',
                'tensorflow[foo]>=2.16 ; (python_version >= "3.10") and sys_platform != "linux"',
            ],
        )

    def test_an_unpinned_tensorflow_and_other_packages(self) -> None:
        self.assertEqual(
            MERGE_MODULE.tensorflow_gpu_lines("tensorflow"),
            ['tensorflow[and-cuda] ; sys_platform == "linux"', 'tensorflow ; sys_platform != "linux"'],
        )
        self.assertEqual(MERGE_MODULE.tensorflow_gpu_lines("tensorflow-io==0.37.1"), ["tensorflow-io==0.37.1"])

    def test_the_torch_index_is_still_added(self) -> None:
        lines = MERGE_MODULE.build_gpu_lines(["tensorflow==2.20.0", "torch==2.5.0"])
        self.assertTrue(lines[0].startswith("--extra-index-url https://download.pytorch.org/whl/"))
        self.assertIn("torch==2.5.0", lines)

    def test_every_gpu_line_is_a_valid_requirement(self) -> None:
        pattern = re.compile(r'^tensorflow(\[[a-z,-]+\])?(==2\.20\.0)? ; sys_platform [!=]= "linux"$')
        for line in MERGE_MODULE.tensorflow_gpu_lines("tensorflow==2.20.0"):
            self.assertRegex(line, pattern)


class VersionCellSnippetTests(unittest.TestCase):
    def _lookup(self, config: object, notebook_name: str) -> str:
        """Run the lookup lines of the live snippet."""
        code = "\n".join(line.strip() for line in MIGRATION.UPLOAD_NEW.splitlines() if not line.strip().startswith("#"))
        code = code.replace("\n", " ", 1)  # the generator expression spans two lines
        scope: dict[str, object] = {"config": config, "notebook_name": notebook_name}
        exec(code, scope)  # noqa: S102 - the snippet's own two lines, from this repository
        return str(scope["latest_version"])

    def test_the_grouped_file_written_by_sync_notebook_versions_is_read(self) -> None:
        self.assertEqual(self._lookup({"StarDist_2D": {"StarDist_2D_ZeroCostDL4Mic": "1.0.0"}}, "StarDist_2D_ZeroCostDL4Mic"), "1.0.0")

    def test_a_missing_notebook_or_an_empty_file_gives_an_empty_version(self) -> None:
        self.assertEqual(self._lookup({"A": {"x": "1"}}, "y"), "")
        self.assertEqual(self._lookup(None, "y"), "")


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path, text: str, newline: str = "\n") -> Path:
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
    def test_a_0_1_21_app_gets_both_changes_and_a_second_run_changes_nothing(self) -> None:
        merge = self.put(MERGE, old_merge())
        upload = self.put(UPLOAD_DOC, old_upload())
        output = self.run_migration()
        self.assertIn(f"{MERGE}: updated", output)
        self.assertIn(f"{UPLOAD_DOC}: updated", output)
        self.assertEqual(merge.read_text(encoding="utf-8"), live(MERGE))
        self.assertEqual(upload.read_text(encoding="utf-8"), live(UPLOAD_DOC))
        before = (merge.read_bytes(), upload.read_bytes())
        again = self.run_migration()
        self.assertIn("unchanged", again)
        self.assertIn("no repository changes were required", again)
        self.assertEqual((merge.read_bytes(), upload.read_bytes()), before)

    def test_crlf_files_keep_their_line_endings(self) -> None:
        merge = self.put(MERGE, old_merge(), newline="\r\n")
        self.assertIn(f"{MERGE}: updated", self.run_migration())
        data = merge.read_bytes()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertEqual(data.decode("utf-8").replace("\r\n", "\n"), live(MERGE))

    def test_a_customised_merge_script_is_skipped_and_left_as_it_is(self) -> None:
        custom = old_merge().replace("                line = rewrite_tensorflow_for_gpu(line)\n", "                line = my_rewrite(line)\n")
        merge = self.put(MERGE, custom)
        output = self.run_migration()
        self.assertIn(f"{MERGE}: SKIPPED", output)
        self.assertEqual(merge.read_text(encoding="utf-8"), custom)

    def test_a_customised_docstring_does_not_block_the_code_change(self) -> None:
        custom = old_merge().replace(MIGRATION.MERGE_DOC_OLD, "My own description.\n")
        merge = self.put(MERGE, custom)
        self.assertIn(f"{MERGE}: updated", self.run_migration())
        self.assertIn(MIGRATION.MERGE_DONE, merge.read_text(encoding="utf-8"))

    def test_missing_files_are_not_created(self) -> None:
        output = self.run_migration()
        self.assertIn(f"{MERGE}: SKIPPED, file not found", output)
        self.assertFalse((self.repo / MERGE).exists())
        self.assertFalse((self.repo / UPLOAD_DOC).exists())

    def test_the_migrated_merge_script_compiles_and_writes_the_new_gpu_lines(self) -> None:
        self.put(MERGE, old_merge())
        self.run_migration()
        module = load(self.repo / MERGE, "migrated_merge_0_1_22")
        self.assertIn('tensorflow==2.20.0 ; sys_platform != "linux"', module.build_gpu_lines(["tensorflow==2.20.0"]))


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_21(self) -> None:
        merge = self.put(MERGE, old_merge())
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        sync = str(self.repo / ".template_sync/sync.py")
        command = [sys.executable, sync, "--from-version", "0.1.21", "--to-version", "0.1.22", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.22]", result.stdout)
        self.assertEqual(merge.read_text(encoding="utf-8"), live(MERGE))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
