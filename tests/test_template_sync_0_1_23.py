"""Tests of template 0.1.23: the release check for template placeholders and the migration that repairs apps (LabConstrictor#40)."""
from __future__ import annotations

import importlib.util
import json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _v0_1_20 import _without_placeholder_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_22_to_v0_1_23.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
CHECK_PATH = ROOT / ".tools/python/check_placeholders.py"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load(MIGRATION_PATH, "migration_0_1_23")
CHECK = load(CHECK_PATH, "check_placeholders_0_1_23")
WORKFLOW = MIGRATION.RELEASE_WORKFLOW


def live(relative: Path | str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def workflow_0_1_22() -> str:
    return _without_placeholder_check((ROOT / WORKFLOW).read_bytes()).decode("utf-8")


def lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


class TemplateConsistencyTests(unittest.TestCase):
    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = live(".template_sync/manifest.yaml")
        self.assertRegex(text, r"template_version: 0\.1\.(2[3-9]|[3-9][0-9])\b")
        self.assertIn("script: migrations/v0_1_22_to_v0_1_23.py", text)

    def test_chains_from_every_older_version_reach_0_1_23(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_23")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.15", "0.1.20", "0.1.22"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.23")
            self.assertEqual(chain[-1]["to"], "0.1.23", start)

    def test_the_design_note_is_linked(self) -> None:
        self.assertIn("(migration_0_1_23.md)", live(".tools/docs/README.md"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_23.md").is_file())

    def test_the_resource_is_the_live_check_script(self) -> None:
        self.assertEqual((MIGRATION.RESOURCE_ROOT / MIGRATION.CHECK_SCRIPT).read_bytes(), CHECK_PATH.read_bytes())

    def test_the_live_workflow_is_the_0_1_22_workflow_migrated(self) -> None:
        text = live(WORKFLOW)
        self.assertEqual(text.count("python .tools/python/check_placeholders.py"), 2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "release_constructor.yml"
            path.write_text(workflow_0_1_22(), encoding="utf-8", newline="\n")
            helpers = MIGRATION._load("v0_1_9_to_v0_1_10.py", "helpers_for_workflow_test")
            self.assertEqual(MIGRATION._add_check_step(helpers, path), "updated: the check runs after bump_Welcome_notebook.py in 2 job(s)")
            self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_the_check_runs_after_the_welcome_notebook_and_before_the_commit_and_the_build(self) -> None:
        text = live(WORKFLOW)
        # (job, start of its update step, the step the check must come before)
        jobs = (("bump-version", "- name: Sync versioned files\n", "Commit updated versioned files"),
                ("build", "Sync versioned files and populate", "Create constructor environment"))
        for job, step, later in jobs:
            with self.subTest(job=job):
                check = text.index("python .tools/python/check_placeholders.py", text.index(step))
                self.assertLess(text.rindex("python .tools/python/bump_Welcome_notebook.py", 0, check), check)
                self.assertLess(check, text.index(later))

    def test_the_raw_template_is_refused_by_its_own_check(self) -> None:
        problems = CHECK.check(ROOT)
        self.assertEqual(len(problems), 1)
        self.assertIn("raw LabConstrictor template", problems[0])


class CheckScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.put("construct.yaml", "name: My_App\nversion: 0.0.1\n")
        self.put("app/bash_bat_scripts/post_install.sh", 'NAME="$PREFIX/My App"\n"$PYTHON_EXE" -c "import my_app; print(1)"\n')

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: str, text: str) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def run_script(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CHECK_PATH), "--repository-root", str(self.repo)], capture_output=True, text=True)

    def test_an_initialised_app_passes(self) -> None:
        self.put("app/menuinst/notebook_launcher.json", '{"command": ["BASE_PATH_KEYWORD/My App/launch_jupyter.py"]}\n')
        self.put("environment.yaml", "dependencies:\n  - python=PYTHON_VERSION\n  - jupyterlab=JUPYTERLAB_VERSION\n")
        self.put(".tools/docs/x.md", "PYTHON_PROJ_NAME is explained here\n")
        (self.repo / "app/logo").mkdir(parents=True)
        (self.repo / "app/logo/icon.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe PROJECT_NAME \x00")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No template placeholder is left", result.stdout)

    def test_the_issue_40_leftovers_are_reported_with_file_and_line(self) -> None:
        self.put("app/bash_bat_scripts/post_install.sh", 'M="PYTHON_PROJ_NAME_lc_tools"\n"$PYTHON_EXE" -c "import PYTHON_PROJ_NAME; print(1)"\n')
        self.put("app/python_scripts/launch_jupyter.py", 'PROJECT_DISPLAY_NAME = "PROJECT_NAME"\n')
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("app/bash_bat_scripts/post_install.sh:1: the template placeholder PYTHON_PROJ_NAME", result.stderr)
        self.assertIn("app/bash_bat_scripts/post_install.sh:2: the template placeholder PYTHON_PROJ_NAME", result.stderr)
        self.assertIn("app/python_scripts/launch_jupyter.py:1: the template placeholder PROJECT_NAME", result.stderr)
        self.assertIn("migration_0_1_23.md", result.stderr)

    def test_a_longer_name_is_reported_once_under_its_own_name(self) -> None:
        self.put("app/bash_bat_scripts/pre_uninstall.bat", "SET ARP=UNDERSCORED_PROJECT_NAME\nSET ROOT=%PROJECT_ROOT%\n")
        problems = CHECK.check(self.repo)
        self.assertEqual(len(problems), 1)
        self.assertIn("UNDERSCORED_PROJECT_NAME", problems[0])

    def test_construct_setup_and_environment_are_checked(self) -> None:
        self.put("setup.py", 'setup(name="PYTHON_PROJ_NAME")\n')
        self.put("environment.yaml", "name: LOWER_PROJ_NAME\n")
        problems = "\n".join(CHECK.check(self.repo))
        self.assertIn("setup.py:1", problems)
        self.assertIn("environment.yaml:1", problems)


class MigrationCase(unittest.TestCase):
    PACKAGE = "my_app"
    NAME = "My App"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.helpers = MIGRATION._load("v0_1_9_to_v0_1_10.py", "helpers_for_tests_0_1_23")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def put(self, relative: Path | str, text: str, newline: str = "\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8"))
        return path

    def initialised(self, relative: Path | str, leave: tuple[str, ...] = ()) -> str:
        """A live template file as the old initializer left it: every placeholder replaced except those in `leave`."""
        text = live(relative)
        values = {"UNDERSCORED_PROJECT_NAME": self.NAME.replace(" ", "_"), "PYTHON_PROJ_NAME": self.PACKAGE, "PROJECT_NAME": self.NAME,
                  "VERSION_NUMBER": "0.0.1", "GITHUB_OWNER": "someone", "GITHUB_REPO_NAME": "my-app"}
        for name, value in values.items():
            if name not in leave and not (str(relative).endswith("Welcome_template.ipynb") and name.startswith("GITHUB")):
                text = MIGRATION.placeholder_pattern(name).sub(value, text)
        return text

    def put_app(self, leave_post_install: bool = True, leave_launcher: bool = True, leave_welcome: bool = True) -> None:
        """A 0.1.22 app made by the old initializer: PYTHON_PROJ_NAME left in post_install, PROJECT_NAME in the launcher."""
        self.put("construct.yaml", f"name: {self.NAME.replace(' ', '_')}\nversion: 0.0.1\n")
        self.put("setup.py", f'setup(name="{self.PACKAGE}")\n')
        self.put(f"src/{self.PACKAGE}/__init__.py", "")
        self.put(f"src/{self.PACKAGE}/tools.py", "x = 1\n")
        self.put(MIGRATION.NOTEBOOK_LAUNCHER, json.dumps({"menu_name": self.NAME, "menu_items": [{"name": self.NAME}]}) + "\n")
        self.put(MIGRATION.POST_INSTALL_SH, self.initialised(MIGRATION.POST_INSTALL_SH, ("PYTHON_PROJ_NAME",) if leave_post_install else ()))
        self.put(MIGRATION.POST_INSTALL_BAT, self.initialised(MIGRATION.POST_INSTALL_BAT, ("PYTHON_PROJ_NAME",) if leave_post_install else ()), "\r\n")
        self.put(MIGRATION.LAUNCHER, self.initialised(MIGRATION.LAUNCHER, ("PROJECT_NAME",) if leave_launcher else ()))
        self.put(MIGRATION.WELCOME_TEMPLATE, self.initialised(MIGRATION.WELCOME_TEMPLATE, ("PROJECT_NAME",) if leave_welcome else ()))
        self.put(WORKFLOW, workflow_0_1_22())
        (self.repo / ".tools/python").mkdir(parents=True, exist_ok=True)

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            MIGRATION.migrate(self.repo, {})
        return buffer.getvalue()


class MigrationBehaviourTests(MigrationCase):
    def test_a_broken_app_is_repaired_passes_the_check_and_a_second_run_changes_nothing(self) -> None:
        self.put_app()
        self.assertTrue(CHECK.check(self.repo))
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.POST_INSTALL_SH}: updated: PYTHON_PROJ_NAME -> my_app", output)
        self.assertIn(f"{MIGRATION.POST_INSTALL_BAT}: updated: PYTHON_PROJ_NAME -> my_app", output)
        self.assertIn(f"{MIGRATION.LAUNCHER}: updated: PROJECT_NAME -> My App", output)
        self.assertIn(f"{MIGRATION.WELCOME_TEMPLATE}: updated: PROJECT_NAME -> My App", output)
        self.assertIn(f"{MIGRATION.CHECK_SCRIPT}: updated: created", output)
        self.assertIn(f"{WORKFLOW}: updated: the check runs after bump_Welcome_notebook.py in 2 job(s)", output)
        sh = lf(self.repo / MIGRATION.POST_INSTALL_SH)
        self.assertIn('-c "import my_app; print(', sh)
        self.assertIn('LC_TOOLS_MODULE="my_app_lc_tools"', sh)
        self.assertIn('PROJECT_DISPLAY_NAME = "My App"', lf(self.repo / MIGRATION.LAUNCHER))
        self.assertEqual(lf(self.repo / WORKFLOW), live(WORKFLOW))
        self.assertEqual((self.repo / MIGRATION.CHECK_SCRIPT).read_bytes(), CHECK_PATH.read_bytes())
        self.assertEqual(CHECK.check(self.repo), [])
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        again = self.run_migration()
        self.assertIn("no repository changes were required", again)
        self.assertEqual({p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}, before)

    def test_a_healthy_app_only_gets_the_check(self) -> None:
        self.put_app(leave_post_install=False, leave_launcher=False, leave_welcome=False)
        scripts = {p: (self.repo / p).read_bytes() for p in MIGRATION.PLACEHOLDER_FILES}
        output = self.run_migration()
        for relative in MIGRATION.PLACEHOLDER_FILES:
            self.assertIn(f"{relative}: unchanged: no placeholder left", output)
        self.assertEqual({p: (self.repo / p).read_bytes() for p in MIGRATION.PLACEHOLDER_FILES}, scripts)
        self.assertIn(f"{MIGRATION.CHECK_SCRIPT}: updated: created", output)

    def test_the_bat_file_keeps_crlf(self) -> None:
        self.put_app()
        self.run_migration()
        data = (self.repo / MIGRATION.POST_INSTALL_BAT).read_bytes()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertIn(b"import my_app;", data)

    def test_an_unknown_package_is_skipped_and_left_as_it_is(self) -> None:
        self.put_app()
        (self.repo / "setup.py").unlink()
        self.put("src/other_pkg/__init__.py", "")
        before = (self.repo / MIGRATION.POST_INSTALL_SH).read_bytes()
        output = self.run_migration()
        self.assertIn(f"{MIGRATION.POST_INSTALL_SH}: SKIPPED: PYTHON_PROJ_NAME is still there, but the Python package", output)
        self.assertEqual((self.repo / MIGRATION.POST_INSTALL_SH).read_bytes(), before)
        self.assertIn(f"{MIGRATION.LAUNCHER}: updated", output)

    def test_the_app_name_falls_back_to_the_launcher_display_name(self) -> None:
        self.put_app(leave_launcher=False)
        (self.repo / MIGRATION.NOTEBOOK_LAUNCHER).unlink()
        self.assertIn(f"{MIGRATION.WELCOME_TEMPLATE}: updated: PROJECT_NAME -> My App", self.run_migration())

    def test_a_customised_workflow_and_an_own_check_script_are_skipped(self) -> None:
        self.put_app()
        self.put(WORKFLOW, "name: our own release\n")
        self.put(MIGRATION.CHECK_SCRIPT, "print('ours')\n")
        output = self.run_migration()
        self.assertIn(f"{WORKFLOW}: SKIPPED: the bump_Welcome_notebook.py command was not found", output)
        self.assertIn(f"{MIGRATION.CHECK_SCRIPT}: SKIPPED: the repository has its own check_placeholders.py", output)
        self.assertEqual(lf(self.repo / WORKFLOW), "name: our own release\n")

    def test_the_raw_template_is_not_touched(self) -> None:
        self.put("construct.yaml", "name: UNDERSCORED_PROJECT_NAME\n")
        self.put(MIGRATION.POST_INSTALL_SH, live(MIGRATION.POST_INSTALL_SH))
        output = self.run_migration()
        self.assertIn("SKIPPED: this repository is not initialised", output)
        self.assertEqual(lf(self.repo / MIGRATION.POST_INSTALL_SH), live(MIGRATION.POST_INSTALL_SH))

    def test_missing_files_are_not_created_except_the_check(self) -> None:
        self.put("construct.yaml", "name: My_App\n")
        (self.repo / ".tools/python").mkdir(parents=True)
        output = self.run_migration()
        for relative in (*MIGRATION.PLACEHOLDER_FILES, WORKFLOW):
            self.assertIn(f"{relative}: not present in this repository", output)
            self.assertFalse((self.repo / relative).exists())

    @unittest.skipUnless(shutil.which("bash"), "bash is not available")
    def test_the_repaired_post_install_sh_is_valid_shell(self) -> None:
        self.put_app()
        self.run_migration()
        result = subprocess.run([shutil.which("bash") or "bash", "-n", str(self.repo / MIGRATION.POST_INSTALL_SH)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ChainTests(MigrationCase):
    def test_the_sync_script_runs_the_migration_from_0_1_22(self) -> None:
        self.put_app()
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync")
        manifest = self.repo / ".template_sync/manifest.yaml"  # sync.py checks the target against the manifest: stop the chain at 0.1.23
        manifest.write_text(re.sub(r"template_version: [0-9.]+", "template_version: 0.1.23", manifest.read_text(encoding="utf-8")), encoding="utf-8")
        sync = str(self.repo / ".template_sync/sync.py")
        command = [sys.executable, sync, "--from-version", "0.1.22", "--to-version", "0.1.23", "--repository-root", str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.23]", result.stdout)
        self.assertIn('import my_app;', lf(self.repo / MIGRATION.POST_INSTALL_SH))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("no repository changes were required", again.stdout)


if __name__ == "__main__":
    unittest.main()
