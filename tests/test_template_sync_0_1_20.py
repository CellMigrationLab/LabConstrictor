"""Tests of template 0.1.20: the workflow race fix, the lock files of the pip requirements, the launcher that starts fresh, and their migration."""
from __future__ import annotations

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
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_19_to_v0_1_20.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
LOCK_SCRIPT_PATH = ROOT / ".tools/python/lock_requirements.py"
BUMP_PATH = ROOT / ".tools/python/bump_constructor.py"
LAUNCHER_PATH = ROOT / "app/python_scripts/launch_jupyter.py"
NOTEBOOK_WORKFLOW = ROOT / ".github/workflows/update_on_notebook_change.yml"
SRC_WORKFLOW = ROOT / ".github/workflows/update_on_src_change.yaml"
BASH = shutil.which("bash")
GIT = shutil.which("git")


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_20")
HELPERS = MIGRATION._load_helpers()


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def steps(workflow: Path) -> dict[str, dict]:
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    (job,) = data["jobs"].values()
    return {step["name"]: step for step in job["steps"]}


# --------------------------------------------------------------------------------------------------------------------------------
# The template itself
# --------------------------------------------------------------------------------------------------------------------------------
class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.20", text)
        self.assertIn("script: migrations/v0_1_19_to_v0_1_20.py", text)

    def test_chains_from_every_older_version_reach_0_1_20(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_20")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.15", "0.1.18", "0.1.19"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.20")
            self.assertEqual(chain[-1]["to"], "0.1.20", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_20.md)", (ROOT / ".tools/docs/README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_20.md").is_file())

    def test_resources_are_identical_to_the_template_files(self) -> None:
        for relative in MIGRATION.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    (MIGRATION.RESOURCE_ROOT / relative).read_bytes(),
                    (ROOT / relative).read_bytes(),
                    "update .template_sync/resources/v0_1_19_to_v0_1_20 when the template file changes",
                )

    def test_the_previous_resources_are_the_0_1_19_files(self) -> None:
        """The 0.1.19 copies are what the migration compares an app's file with: each must differ from the new file (else nothing is replaced)."""
        for relative in MIGRATION.REPLACED_FILES:
            with self.subTest(file=str(relative)):
                self.assertNotEqual(lf(MIGRATION.PREVIOUS_ROOT / relative), lf(ROOT / relative))

    def test_the_live_scripts_hold_the_new_blocks_once(self) -> None:
        for relative, blocks in ((MIGRATION.POST_INSTALL_SH, MIGRATION.SH_BLOCKS), (MIGRATION.POST_INSTALL_BAT, MIGRATION.BAT_BLOCKS)):
            text = lf(ROOT / relative)
            for old, new in blocks:
                with self.subTest(file=str(relative), block=old.splitlines()[0]):
                    self.assertEqual(text.count(new), 1)
                    self.assertNotIn(old, text.replace(new, ""), "the 0.1.19 block is left only inside the new one")
        bump = lf(BUMP_PATH)
        self.assertEqual(bump.count(MIGRATION.BUMP_SNIPPET + MIGRATION.BUMP_FUNCTION_ANCHOR), 1)
        self.assertEqual(bump.count(MIGRATION.BUMP_CALL_NEW), 1)
        self.assertIn(MIGRATION.UV_PIN, lf(ROOT / MIGRATION.TOOLS_REQUIREMENTS).splitlines())
        self.assertIn(MIGRATION.USAGE_NEW, lf(ROOT / MIGRATION.USAGE_DOC))

    def test_the_menu_shortcut_closes_the_windows_terminal_after_enter(self) -> None:
        data = json.loads(lf(ROOT / MIGRATION.MENU))
        (item,) = data["menu_items"]
        self.assertTrue(item["terminal"])
        self.assertEqual(item["platforms"]["win"]["command"], item["command"] + ["&", "exit"])
        for platform in ("linux", "osx"):
            self.assertNotIn("command", item["platforms"][platform])

    def test_the_workflows_no_longer_share_a_concurrency_group_and_never_use_the_auto_commit_action(self) -> None:
        groups = set()
        for workflow in (NOTEBOOK_WORKFLOW, SRC_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
                groups.add(data["concurrency"]["group"])
                self.assertFalse(data["concurrency"]["cancel-in-progress"])
                text = workflow.read_text(encoding="utf-8")
                self.assertNotIn("git-auto-commit-action", text)
                checkout = steps(workflow)["Checkout repository"]
                self.assertNotIn("ref", checkout.get("with", {}), "the scripts compare the triggering commit with its parent: keep github.sha")
                commit = steps(workflow)["Commit updated files"]["run"]
                self.assertIn('git rebase --autostash "origin/$BRANCH"', commit)
                self.assertIn('git push origin "HEAD:refs/heads/$BRANCH"', commit)
        self.assertEqual(len(groups), 2)

    def test_the_notebook_workflow_locks_after_merging_and_reverts_only_for_the_conda_test(self) -> None:
        names = list(steps(NOTEBOOK_WORKFLOW))
        self.assertEqual(names.index("Lock requirements"), names.index("Run merge script") + 1)
        self.assertLess(names.index("Lock requirements"), names.index("Check for changes"))
        self.assertIn("lock_requirements.py", steps(NOTEBOOK_WORKFLOW)["Lock requirements"]["run"])
        revert = steps(NOTEBOOK_WORKFLOW)["Revert user commit that broke requirements"]
        self.assertIn("steps.test-conda-env.outcome == 'failure'", revert["if"])
        self.assertIn("failure()", revert["if"])

    def test_the_conda_test_installs_the_lock_file(self) -> None:
        text = lf(ROOT / MIGRATION.TEST_CONDA)
        self.assertIn('REQUIREMENTS_FILE="requirements.lock.txt"', text)
        self.assertIn('pip install --prefer-binary -r "$REQUIREMENTS_FILE"', text)
        self.assertIn("pip check", text)


# --------------------------------------------------------------------------------------------------------------------------------
# The workflow steps themselves, run with bash and git against a local "origin" that moved while the run worked
# --------------------------------------------------------------------------------------------------------------------------------
@unittest.skipUnless(BASH and GIT, "bash and git are needed")
class WorkflowScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "user",
            "GIT_AUTHOR_EMAIL": "user@example.com",
            "GIT_COMMITTER_NAME": "user",
            "GIT_COMMITTER_EMAIL": "user@example.com",
            "GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        (self.tmp / "gitconfig").write_text("[init]\n\tdefaultBranch = main\n[core]\n\tautocrlf = false\n", encoding="utf-8")
        # `sleep` of the retry loop: instant in the tests
        fake_bin = self.tmp / "bin"
        fake_bin.mkdir()
        (fake_bin / "sleep").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (fake_bin / "sleep").chmod(0o755)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env["PATH"]
        self.origin = self.tmp / "origin.git"
        self.git(self.tmp, "init", "--bare", "-q", str(self.origin))
        self.seed = self.tmp / "seed"
        self.git(self.tmp, "clone", "-q", str(self.origin), str(self.seed))
        self.write(self.seed / "requirements.txt", "pandas==2.2.2\n")
        self.write(self.seed / "requirements.lock.txt", "pandas==2.2.2\nnumpy==2.0.0\n")
        self.write(self.seed / ".tools/meta/src_change.yaml", 'src_last_modified: "old"\n')
        self.write(self.seed / "notebooks/A/A.ipynb", "{}\n")
        self.write(self.seed / "src/code.py", "x = 1\n")
        self.commit(self.seed, "base")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run([GIT or "git", *args], cwd=cwd, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"git {' '.join(args)}: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self, repo: Path, message: str) -> str:
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", message)
        self.git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")
        return self.git(repo, "rev-parse", "HEAD")

    def runner_checkout(self, sha: str) -> Path:
        """What actions/checkout does for a push: the branch at the commit that triggered the run (fetch-depth 0)."""
        work = self.tmp / f"run-{sha[:7]}"
        self.git(self.tmp, "clone", "-q", str(self.origin), str(work))
        self.git(work, "checkout", "-q", "-B", "main", sha)
        return work

    def run_step(self, workflow: Path, name: str, cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
        step = steps(workflow)[name]
        script = self.tmp / "step.sh"
        script.write_bytes(step["run"].encode("utf-8"))
        merged = {**self.env, **{k: str(v) for k, v in step.get("env", {}).items() if "${{" not in str(v)}, **env}
        # GitHub runs `run:` steps with `bash -e {0}`
        return subprocess.run([BASH or "bash", "-e", str(script)], cwd=cwd, env=merged, capture_output=True, text=True)

    def origin_log(self) -> list[str]:
        self.git(self.seed, "fetch", "-q")
        return self.git(self.seed, "log", "--format=%s", "origin/main").splitlines()

    def test_the_src_commit_is_rebased_onto_a_branch_that_moved_while_the_run_waited(self) -> None:
        trigger = self.git(self.seed, "rev-parse", "HEAD")
        work = self.runner_checkout(trigger)
        # the notebook workflow pushed its commit in the meantime (CellMigrationLab/LabChronicle run 41800906840)
        self.write(self.seed / "requirements.lock.txt", "pandas==2.2.2\nnumpy==2.1.0\n")
        self.commit(self.seed, "GitHub Action - Updated files because of notebook and/or requirements changes")
        self.write(work / ".tools/meta/src_change.yaml", 'src_last_modified: "new"\n')
        result = self.run_step(SRC_WORKFLOW, "Commit updated files", work, BRANCH="main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rebasing onto the latest main", result.stdout)
        self.assertEqual(self.origin_log()[:2], ["GitHub Action - Updated src change file", "GitHub Action - Updated files because of notebook and/or requirements changes"])
        self.git(self.seed, "merge", "-q", "--ff-only", "origin/main")
        self.assertIn("new", (self.seed / ".tools/meta/src_change.yaml").read_text(encoding="utf-8"))
        self.assertIn("numpy==2.1.0", (self.seed / "requirements.lock.txt").read_text(encoding="utf-8"))

    def test_the_notebook_commit_takes_only_its_files_including_a_removed_lock_file(self) -> None:
        trigger = self.git(self.seed, "rev-parse", "HEAD")
        work = self.runner_checkout(trigger)
        self.write(self.seed / ".tools/meta/src_change.yaml", 'src_last_modified: "from the src workflow"\n')
        self.commit(self.seed, "GitHub Action - Updated src change file")
        (work / "requirements.lock.txt").unlink()  # lock_requirements.py removed a stale lock file
        self.write(work / "requirements_gpu.lock.txt", "torch==2.7.1\n")
        self.write(work / "notebooks/A/A.ipynb", '{"cells": []}\n')
        self.write(work / "src/code.py", "x = 2\n")  # not a file of this workflow: never committed
        result = self.run_step(NOTEBOOK_WORKFLOW, "Commit updated files", work, BRANCH="main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.git(self.seed, "fetch", "-q")
        changed = self.git(self.seed, "show", "--name-status", "--format=", "origin/main").splitlines()
        self.assertEqual(sorted(changed), sorted(["D\trequirements.lock.txt", "A\trequirements_gpu.lock.txt", "M\tnotebooks/A/A.ipynb"]))
        self.assertEqual(self.git(self.seed, "log", "-1", "--format=%s", "origin/main~1"), "GitHub Action - Updated src change file")

    def test_a_conflicting_commit_fails_with_a_message_and_pushes_nothing(self) -> None:
        trigger = self.git(self.seed, "rev-parse", "HEAD")
        work = self.runner_checkout(trigger)
        self.write(self.seed / "requirements.lock.txt", "pandas==2.2.2\nnumpy==3.0.0\n")
        moved = self.commit(self.seed, "someone else")
        self.write(work / "requirements.lock.txt", "pandas==2.2.2\nnumpy==2.9.0\n")
        result = self.run_step(NOTEBOOK_WORKFLOW, "Commit updated files", work, BRANCH="main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::The commit of this run conflicts with the latest main", result.stdout)
        self.git(self.seed, "fetch", "-q")
        self.assertEqual(self.git(self.seed, "rev-parse", "origin/main"), moved)

    def test_the_revert_reverts_a_merge_and_a_plain_commit_on_top_of_the_latest_branch(self) -> None:
        for kind in ("merge", "plain"):
            with self.subTest(kind=kind):
                if kind == "merge":
                    base = self.git(self.seed, "rev-parse", "HEAD")
                    self.git(self.seed, "checkout", "-q", "-b", "side")
                    self.write(self.seed / "requirements.txt", "pandas==2.2.2\nbroken==0\n")
                    self.git(self.seed, "add", "-A")
                    self.git(self.seed, "commit", "-q", "-m", "break")
                    self.git(self.seed, "checkout", "-q", "main")
                    self.git(self.seed, "reset", "-q", "--hard", base)
                    self.write(self.seed / "notebooks/A/notes.md", "x\n")
                    self.git(self.seed, "add", "-A")
                    self.git(self.seed, "commit", "-q", "-m", "other work")
                    self.git(self.seed, "merge", "-q", "--no-ff", "-m", "Merge branch side", "side")
                    self.git(self.seed, "push", "-q", "origin", "HEAD:refs/heads/main")
                    bad = self.git(self.seed, "rev-parse", "HEAD")
                else:
                    self.write(self.seed / "requirements.txt", "pandas==2.2.2\nbroken==1\n")
                    bad = self.commit(self.seed, "break again")
                work = self.runner_checkout(bad)
                self.write(work / "requirements.txt", "half written by the merge script\n")  # left over by the failed run
                # the src workflow committed while the conda test ran
                self.write(self.seed / ".tools/meta/src_change.yaml", f'src_last_modified: "{kind}"\n')
                self.commit(self.seed, f"src {kind}")
                result = self.run_step(NOTEBOOK_WORKFLOW, "Revert user commit that broke requirements", work, BRANCH="main", BAD_COMMIT=bad)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.git(self.seed, "fetch", "-q")
                self.assertTrue(self.git(self.seed, "log", "-1", "--format=%s", "origin/main").startswith("Revert "))
                self.assertEqual(self.git(self.seed, "log", "-1", "--format=%s", "origin/main~1"), f"src {kind}")
                self.git(self.seed, "checkout", "-q", "main")
                self.git(self.seed, "reset", "-q", "--hard", "origin/main")
                self.assertEqual((self.seed / "requirements.txt").read_text(encoding="utf-8"), "pandas==2.2.2\n")


# --------------------------------------------------------------------------------------------------------------------------------
# lock_requirements.py (uv is replaced by a fake: the tests need no network)
# --------------------------------------------------------------------------------------------------------------------------------
class LockScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.lock = load(LOCK_SCRIPT_PATH, "lock_requirements_under_test")
        (self.root / "environment.yaml").write_text(
            "name: demo\ndependencies:\n- python=3.11.1\n- conda\n- git\n- pip>=24.2\n- setuptools\n- certifi\n- jupyterlab=4.4.0\n- pip:\n  - ignored\n",
            encoding="utf-8",
        )
        self.calls: list[dict] = []

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def fake_uv(self, requirements: Path, python_version: str, constraint_files: list[Path], no_emit: list[str]) -> str:
        self.calls.append({
            "file": requirements.name,
            "python": python_version,
            "constraints": [c.read_text(encoding="utf-8") for c in constraint_files],
            "no_emit": no_emit,
        })
        if "unsolvable" in requirements.read_text(encoding="utf-8"):
            raise RuntimeError("No solution found when resolving dependencies")
        return "# uv comment\nnumpy==2.4.6 ; python_full_version < '3.12'\npandas==2.2.2\n"

    def run_lock(self) -> str:
        buffer = StringIO()
        with mock.patch.object(self.lock, "run_uv", self.fake_uv), mock.patch.object(self.lock, "uv_version", lambda: "uv 0.13.3"), redirect_stdout(buffer):
            self.assertEqual(self.lock.main(["--root", str(self.root)]), 0)
        return buffer.getvalue()

    def test_the_environment_gives_the_python_the_conda_names_and_the_conda_pins(self) -> None:
        python, names, constraints = self.lock.read_environment(self.root / "environment.yaml")
        self.assertEqual(python, "3.11.1")
        self.assertEqual(names, ["certifi", "conda", "git", "jupyterlab", "pip", "setuptools"])
        self.assertEqual(constraints, ["jupyterlab==4.4.0.*"])

    def test_the_template_placeholders_lock_nothing(self) -> None:
        (self.root / "environment.yaml").write_text("dependencies:\n- python=PYTHON_VERSION\n- jupyterlab=JUPYTERLAB_VERSION\n", encoding="utf-8")
        (self.root / "requirements.txt").write_text("pandas\n", encoding="utf-8")
        self.assertIn("no exact Python version", self.run_lock())
        self.assertFalse((self.root / "requirements.lock.txt").exists())

    def test_a_lock_file_is_written_once_and_kept_while_the_inputs_do_not_change(self) -> None:
        requirements = self.root / "requirements.txt"
        requirements.write_text("# Generated by merge_requirements.py on 2026-11-04T08:30:40Z\npandas==2.2.2\n", encoding="utf-8")
        self.assertIn("requirements.lock.txt: written", self.run_lock())
        lock = (self.root / "requirements.lock.txt").read_bytes()
        text = lock.decode("utf-8")
        self.assertNotIn(b"\r\n", lock)
        self.assertIn("uv 0.13.3, universal resolution for Python 3.11.1", text)
        self.assertIn("numpy==2.4.6 ; python_full_version < '3.12'\npandas==2.2.2\n", text)
        self.assertNotIn("# uv comment", text)
        self.assertEqual(self.calls[0]["python"], "3.11.1")
        self.assertEqual(self.calls[0]["constraints"], ["jupyterlab==4.4.0.*\n"])
        self.assertNotIn("git", self.calls[0]["no_emit"])
        self.assertIn("jupyterlab", self.calls[0]["no_emit"])
        # a new merge only changes the timestamp comment: the lock file is kept and uv is not run again
        requirements.write_text("# Generated by merge_requirements.py on 2026-12-01T00:00:00Z\npandas==2.2.2\n", encoding="utf-8")
        self.assertIn("requirements.lock.txt: up to date (unchanged)", self.run_lock())
        self.assertEqual((self.root / "requirements.lock.txt").read_bytes(), lock)
        self.assertEqual(len(self.calls), 1)
        # a new requirement, or another JupyterLab version, writes it again
        requirements.write_text("pandas==2.2.2\ntqdm\n", encoding="utf-8")
        self.assertIn("requirements.lock.txt: written", self.run_lock())
        env = self.root / "environment.yaml"
        env.write_text(env.read_text(encoding="utf-8").replace("jupyterlab=4.4.0", "jupyterlab=4.5.0"), encoding="utf-8")
        self.assertIn("requirements.lock.txt: written", self.run_lock())
        self.assertEqual(len(self.calls), 3)

    def test_the_index_options_are_copied_and_the_os_file_is_constrained_by_the_base_lock(self) -> None:
        (self.root / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
        (self.root / "requirements_gpu.txt").write_text("--extra-index-url https://download.pytorch.org/whl/cu128\ntorch\n", encoding="utf-8")
        (self.root / "requirements-windows.txt").write_text("pywin32\n", encoding="utf-8")
        self.run_lock()
        gpu = (self.root / "requirements_gpu.lock.txt").read_text(encoding="utf-8")
        self.assertIn("\n--extra-index-url https://download.pytorch.org/whl/cu128\n\nnumpy==", gpu)
        windows_call = next(call for call in self.calls if call["file"] == "requirements-windows.txt")
        self.assertEqual(len(windows_call["constraints"]), 2)
        self.assertIn("pandas==2.2.2", windows_call["constraints"][1])
        self.assertNotIn("# lock-input", windows_call["constraints"][1])
        gpu_call = next(call for call in self.calls if call["file"] == "requirements_gpu.txt")
        self.assertEqual(len(gpu_call["constraints"]), 1, "the GPU file is resolved on its own (its torch is not the CPU torch)")

    def test_a_file_that_cannot_be_locked_removes_its_stale_lock_and_warns(self) -> None:
        requirements = self.root / "requirements.txt"
        requirements.write_text("pandas==2.2.2\n", encoding="utf-8")
        self.run_lock()
        requirements.write_text("pandas==2.2.2\nunsolvable==1\n", encoding="utf-8")
        output = self.run_lock()
        self.assertIn("::warning::", output)
        self.assertIn("requirements.lock.txt: removed", output)
        self.assertFalse((self.root / "requirements.lock.txt").exists())
        self.assertIn("not locked: requirements.txt", output)

    def test_a_lock_file_without_its_requirements_file_is_removed(self) -> None:
        (self.root / "requirements.txt").write_text("pandas\n", encoding="utf-8")
        (self.root / "requirements-macos.lock.txt").write_text("old\n", encoding="utf-8")
        self.assertIn("requirements-macos.lock.txt: removed", self.run_lock())
        self.assertFalse((self.root / "requirements-macos.lock.txt").exists())

    def test_uv_errors_are_reported_as_runtime_errors(self) -> None:
        (self.root / "requirements.txt").write_text("pandas\n", encoding="utf-8")
        failed = subprocess.CompletedProcess([], 2, stdout="", stderr="error: boom")
        with mock.patch.object(self.lock.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                self.lock.run_uv(self.root / "requirements.txt", "3.11.1", [], [])


# --------------------------------------------------------------------------------------------------------------------------------
# bump_constructor.py bundles the lock files
# --------------------------------------------------------------------------------------------------------------------------------
class BumpConstructorTests(unittest.TestCase):
    def test_lock_files_are_mapped_when_they_exist_and_unmapped_when_they_are_gone(self) -> None:
        bump = load(BUMP_PATH, "bump_constructor_0_1_20")
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                Path("requirements.lock.txt").write_text("x\n", encoding="utf-8")
                data = {"extra_files": [
                    {"app/menuinst/Welcome.ipynb": "Demo/notebooks/Welcome.ipynb"},
                    {"requirements_gpu.lock.txt": "Demo/requirements_gpu.lock.txt"},
                ]}
                with redirect_stdout(StringIO()):
                    bump.ensure_lock_files_in_extra_files(data)
                    bump.ensure_lock_files_in_extra_files(data)
            finally:
                os.chdir(cwd)
        self.assertEqual(data["extra_files"], [
            {"app/menuinst/Welcome.ipynb": "Demo/notebooks/Welcome.ipynb"},
            {"requirements.lock.txt": "Demo/requirements.lock.txt"},
        ])


# --------------------------------------------------------------------------------------------------------------------------------
# launch_jupyter.py: a fresh workspace folder, and Enter before the window closes
# --------------------------------------------------------------------------------------------------------------------------------
class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.launcher = load(LAUNCHER_PATH, "launch_jupyter_0_1_20")

    def test_jupyterlab_gets_an_empty_workspace_folder_that_is_removed_afterwards(self) -> None:
        seen: dict[str, object] = {}

        def fake_main() -> int:
            argv = list(sys.argv)
            (arg,) = [a for a in argv if a.startswith("--LabApp.workspaces_dir=")]
            folder = Path(arg.split("=", 1)[1])
            seen.update(argv=argv, folder=folder, empty=folder.is_dir() and not any(folder.iterdir()))
            (folder / "auto-0.jupyterlab-workspace").write_text("{}", encoding="utf-8")  # JupyterLab saves the session
            return 0

        labapp = ModuleType("jupyterlab.labapp")
        labapp.main = fake_main  # type: ignore[attr-defined]
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp) / "Welcome.ipynb"
            notebook.write_text("{}", encoding="utf-8")
            saved_argv = sys.argv
            try:
                with mock.patch.dict(sys.modules, {"jupyterlab": ModuleType("jupyterlab"), "jupyterlab.labapp": labapp}):
                    self.assertEqual(self.launcher.run_jupyter(notebook), 0)
            finally:
                sys.argv = saved_argv
        self.assertTrue(seen["empty"])
        self.assertFalse(Path(str(seen["folder"])).exists())
        argv = seen["argv"]
        assert isinstance(argv, list)
        self.assertIn(str(notebook.resolve()), argv)

    def test_the_window_waits_for_enter_after_a_launch_but_not_for_the_installer_checks(self) -> None:
        cases = {
            (): True,
            ("--no-wait",): False,
            ("--self-test",): False,
            ("--print-ca-bundle",): False,
        }
        for args, waits in cases.items():
            with self.subTest(args=args):
                with mock.patch.object(self.launcher, "_launch", return_value=7), mock.patch.object(self.launcher, "_wait_for_enter") as wait:
                    self.assertEqual(self.launcher.main(list(args)), 7)
                self.assertEqual(wait.called, waits)

    def test_the_prompt_is_asked_only_in_a_terminal(self) -> None:
        tty = mock.Mock()
        tty.isatty.return_value = True
        pipe = mock.Mock()
        pipe.isatty.return_value = False
        for stream, asked in ((tty, True), (pipe, False), (None, False)):
            with self.subTest(asked=asked):
                with mock.patch.object(self.launcher.sys, "stdin", stream), mock.patch("builtins.input") as prompt:
                    self.launcher._wait_for_enter()
                self.assertEqual(prompt.called, asked)
        with mock.patch.object(self.launcher.sys, "stdin", tty), mock.patch("builtins.input", side_effect=EOFError):
            self.launcher._wait_for_enter()  # a closed input never raises


# --------------------------------------------------------------------------------------------------------------------------------
# The migration
# --------------------------------------------------------------------------------------------------------------------------------
CONSTRUCT = """name: LabChronicle
version: 1.2.0

extra_files:
- app/menuinst/Welcome.ipynb: LabChronicle/notebooks/Welcome.ipynb
- requirements.txt: LabChronicle/requirements.txt
"""


class MigrationCase(unittest.TestCase):
    NEWLINES = {
        # line endings of the template files (src workflow and post_install.bat are CRLF in the template)
        MIGRATION.SRC_WORKFLOW: "\r\n",
        MIGRATION.POST_INSTALL_BAT: "\r\n",
    }

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.put("construct.yaml", CONSTRUCT)
        self.replacements = HELPERS.load_replacements(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path | str, text: str, newline: str = "\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8"))
        return path

    def rendered(self, text: str) -> str:
        return str(HELPERS.render_template(text, self.replacements, "\n"))

    def old(self, relative: Path) -> str:
        """The 0.1.19 file of an app (rendered with the app name)."""
        if relative in MIGRATION.REPLACED_FILES:
            return self.rendered(lf(MIGRATION.PREVIOUS_ROOT / relative))
        text = lf(ROOT / relative)
        if relative == MIGRATION.POST_INSTALL_SH:
            for old, new in MIGRATION.SH_BLOCKS:
                text = text.replace(new, old)
        elif relative == MIGRATION.POST_INSTALL_BAT:
            for old, new in MIGRATION.BAT_BLOCKS:
                text = text.replace(new, old)
        elif relative == MIGRATION.BUMP_CONSTRUCTOR:
            text = text.replace(MIGRATION.BUMP_SNIPPET, "").replace(MIGRATION.BUMP_CALL_NEW, MIGRATION.BUMP_CALL_OLD)
        elif relative == MIGRATION.MENU:
            data = json.loads(text)
            del data["menu_items"][0]["platforms"]["win"]["command"]
            text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        elif relative == MIGRATION.TOOLS_REQUIREMENTS:
            text = text.replace(MIGRATION.UV_LINES, "")
        elif relative == MIGRATION.USAGE_DOC:
            text = text.replace(MIGRATION.USAGE_NEW, MIGRATION.USAGE_OLD)
        return self.rendered(text)

    def new(self, relative: Path) -> str:
        return self.rendered(lf(ROOT / relative))

    ALL = (
        *MIGRATION.REPLACED_FILES,
        MIGRATION.TOOLS_REQUIREMENTS,
        MIGRATION.POST_INSTALL_SH,
        MIGRATION.POST_INSTALL_BAT,
        MIGRATION.BUMP_CONSTRUCTOR,
        MIGRATION.MENU,
        MIGRATION.USAGE_DOC,
    )

    def put_0_1_19_app(self, crlf: bool = False) -> None:
        for relative in self.ALL:
            self.put(relative, self.old(relative), "\r\n" if crlf else self.NEWLINES.get(relative, "\n"))

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_a_0_1_19_app_reaches_the_0_1_20_files_and_a_second_run_changes_nothing(self) -> None:
        self.put_0_1_19_app()
        output = self.run_migration()
        for relative in (*self.ALL, MIGRATION.LOCK_SCRIPT):
            with self.subTest(file=str(relative)):
                self.assertRegex(output, rf"{re.escape(str(relative))}: updated")
                self.assertEqual(lf(self.repo / relative), self.new(relative))
        self.assertIn("LabChronicle", lf(self.repo / MIGRATION.LAUNCHER))
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertNotIn("SKIPPED", again)
        self.assertEqual({p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}, before)

    def test_line_endings_are_kept(self) -> None:
        self.put_0_1_19_app(crlf=True)
        self.run_migration()
        for relative in self.ALL:
            with self.subTest(file=str(relative)):
                data = (self.repo / relative).read_bytes()
                self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertNotIn(b"\r\n", (self.repo / MIGRATION.LOCK_SCRIPT).read_bytes(), "a new file is written with LF")

    def test_customised_files_are_skipped_and_left_as_they_are(self) -> None:
        self.put_0_1_19_app()
        custom = {
            MIGRATION.NOTEBOOK_WORKFLOW: self.old(MIGRATION.NOTEBOOK_WORKFLOW).replace("runs-on: ubuntu-latest", "runs-on: ubuntu-22.04"),
            MIGRATION.LAUNCHER: self.old(MIGRATION.LAUNCHER) + "\n# our own line\n",
            MIGRATION.POST_INSTALL_SH: self.old(MIGRATION.POST_INSTALL_SH).replace('-m pip install -r "$PROJECT_ROOT/requirements-macos.txt"', '-m pip install -U -r "$PROJECT_ROOT/requirements-macos.txt"'),
            MIGRATION.BUMP_CONSTRUCTOR: self.old(MIGRATION.BUMP_CONSTRUCTOR).replace(MIGRATION.BUMP_CALL_OLD, "    ensure_requirements_in_extra_files(data, strict=True)\n"),
        }
        for relative, text in custom.items():
            self.put(relative, text, self.NEWLINES.get(relative, "\n"))
        output = self.run_migration()
        for relative, text in custom.items():
            with self.subTest(file=str(relative)):
                self.assertIn(f"{relative}: SKIPPED", output)
                self.assertEqual(lf(self.repo / relative), text)
        self.assertIn(f"{MIGRATION.SRC_WORKFLOW}: updated", output)

    def test_the_menu_variants(self) -> None:
        old = self.old(MIGRATION.MENU)
        cases = {
            "own windows command": (old.replace('"icon": "', '"command": ["cmd"],\n          "icon": "', 1), "SKIPPED: has its own Windows command"),
            "other formatting": (json.dumps(json.loads(old)) + "\n", "SKIPPED: formatted differently"),
            "no terminal": (old.replace('"terminal": true', '"terminal": false'), "SKIPPED: not the template shape"),
            "not json": ("{", "SKIPPED: not valid JSON"),
        }
        for name, (text, message) in cases.items():
            with self.subTest(case=name):
                path = self.put(MIGRATION.MENU, text)
                self.assertIn(message, self.run_migration())
                self.assertEqual(lf(path), text)

    def test_uv_and_the_lock_script_of_an_app_are_kept(self) -> None:
        self.put(MIGRATION.TOOLS_REQUIREMENTS, "pyyaml==6.0.2\nuv>=0.12\n")
        self.put(MIGRATION.LOCK_SCRIPT, "# our own\n")
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.TOOLS_REQUIREMENTS}: already installs uv: unchanged", output)
        self.assertIn(f"{MIGRATION.LOCK_SCRIPT}: SKIPPED: the repository has its own lock_requirements.py", output)
        self.assertEqual(lf(self.repo / MIGRATION.LOCK_SCRIPT), "# our own\n")

    def test_a_tools_requirements_file_without_a_final_newline_gets_uv_on_its_own_line(self) -> None:
        self.put(MIGRATION.TOOLS_REQUIREMENTS, "pyyaml==6.0.2")
        self.run_migration()
        self.assertEqual(lf(self.repo / MIGRATION.TOOLS_REQUIREMENTS), "pyyaml==6.0.2\n" + MIGRATION.UV_LINES)

    def test_missing_files_are_not_created(self) -> None:
        output = self.run_migration()
        for relative in self.ALL:
            with self.subTest(file=str(relative)):
                self.assertIn(f"{relative}: not present in this repository", output)
                self.assertFalse((self.repo / relative).exists())
        self.assertIn(f"{MIGRATION.LOCK_SCRIPT}: SKIPPED: the repository has no .tools/python folder", output)
        self.assertFalse((self.repo / MIGRATION.LOCK_SCRIPT).exists())

    def test_a_labchronicle_like_app_with_its_own_bump_constructor_still_gets_the_lock_function(self) -> None:
        """LabChronicle's bump_constructor.py has no ensure_app_manifest_in_extra_files (it differs from the template): the two anchors suffice."""
        text = self.old(MIGRATION.BUMP_CONSTRUCTOR).replace("    ensure_app_manifest_in_extra_files(data)\n", "")
        path = self.put(MIGRATION.BUMP_CONSTRUCTOR, text)
        self.assertIn(f"{MIGRATION.BUMP_CONSTRUCTOR}: updated", self.run_migration())
        result = lf(path)
        self.assertIn(MIGRATION.BUMP_CALL_NEW, result)
        compile(result, str(path), "exec")


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_19(self) -> None:
        self.put_0_1_19_app()
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        command = [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", "0.1.19", "--to-version", "0.1.20", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.20]", result.stdout)
        self.assertEqual(lf(self.repo / MIGRATION.NOTEBOOK_WORKFLOW), self.new(MIGRATION.NOTEBOOK_WORKFLOW))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)

    @unittest.skipUnless(BASH, "bash is not available")
    def test_the_migrated_post_install_sh_is_valid_shell(self) -> None:
        self.put_0_1_19_app()
        self.run_migration()
        result = subprocess.run([BASH or "bash", "-n", str(self.repo / MIGRATION.POST_INSTALL_SH)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
