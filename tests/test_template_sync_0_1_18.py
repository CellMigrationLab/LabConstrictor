"""Tests of the 0.1.18 migration: new Tools pin, GitHub Actions pinned by SHA, install rules in the install guide."""
from __future__ import annotations

import difflib
import hashlib
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

from _hosts import strip_hosts


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_17_to_v0_1_18.py"
SYNC_PATH = ROOT / ".template_sync/sync.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
APPS_0_1_17 = FIXTURES / "template_0_1_17_apps"
WORKFLOWS_0_1_17 = FIXTURES / "template_0_1_17_workflows"
DOCS_0_1_17 = FIXTURES / "template_0_1_17_docs"
OLD_SCRIPTS = FIXTURES / "template_0_1_15_scripts"
BRIDGE_TEST = FIXTURES / "bridge_test_hooks"
SCRIPT_NAMES = ("post_install.sh", "post_install.bat")
WORKFLOW_NAMES = ("check_app_manifest.yml", "release_constructor.yml", "sync_template.yml", "update_on_notebook_change.yml", "update_on_src_change.yaml")
OLD_PIN = "v0.2.0-rc.1"
NEW_PIN = "v0.3.0-alpha.1"

# The commit SHA of each third-party action tag the template workflows use (the same pins the apps carry after their own pinning pull requests).
PINS = {
    ("actions/checkout", "v4"): "11d5960a326750d5838078e36cf38b85af677262",
    ("actions/setup-python", "v4"): "7f4fc3e22c37d6ff65e88745f38bd3157c663f7c",
    ("actions/upload-artifact", "v7"): "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
    ("tj-actions/changed-files", "v44"): "2d756ea4c53f7f6b397767d8723b3a10a9f35bf2",
    ("conda-incubator/setup-miniconda", "v3"): "fc2d68f6413eb2d87b895e92f8584b5b94a10167",
    ("stefanzweifel/git-auto-commit-action", "v5"): "b863ae1933cb653a53c021fe36dbb774e1fb9403",
    ("softprops/action-gh-release", "v2"): "3bb12739c298aeb8a4eeaf626c5b8d85266b0e65",
    ("peter-evans/create-pull-request", "v6"): "c5a7806660adbe173f04e3e038b0ccdcd758773c",
}
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)@(\S+)(?:[ \t]+#[ \t]*(\S+))?\s*$")

# The three install rules, word for word. Every doc that states a rule must use exactly this sentence.
RULE_PATH = "The install path must contain no space: the installer refuses a path with a space. Use a path such as `C:\\LabConstrictor\\<app>` on Windows or `~/labconstrictor/<app>` on macOS and Linux."
RULE_UPDATE = "On macOS and Windows, update an app by uninstalling the old version first and then installing the new one: the installer does not install over an existing install."
RULE_LINUX = "On Linux, running the installer with `-u` updates in place only if the previous install finished; otherwise delete `<prefix>/pkgs` or uninstall the app and install it again."

CONSTRUCT = """name: Demo_App
version: 1.2.3
icon_image: app/logo/demo.png
extra_files:
- app/menuinst/Welcome.ipynb: DemoApp/notebooks/Welcome.ipynb
- app/menuinst/notebook_launcher.json: DemoApp/notebook_launcher.json
- requirements.txt: DemoApp/requirements.txt
"""


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def pin_view(root: Path) -> dict[str, str]:
    """`snapshot` of the pin tests: the post_install scripts are seen without the lines of the hosts step, which has its own tests."""
    view = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            view[str(path.relative_to(root))] = hashlib.sha256(strip_hosts(path.name, data) if path.name.startswith("post_install.") else data).hexdigest()
    return view


def to_crlf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def to_lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def uses_lines(path: Path) -> list[tuple[str, str, str | None]]:
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = USES.match(line)
        if match:
            found.append((match.group(1), match.group(2), match.group(3)))
    return found


class TemplateConsistencyTests(unittest.TestCase):
    def test_resources_are_identical_to_the_template_files(self) -> None:
        migration = load(MIGRATION_PATH, "migration_0_1_18_resources")
        for relative in migration.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    (migration.RESOURCE_ROOT / relative).read_bytes(),
                    (ROOT / relative).read_bytes(),
                    "update .template_sync/resources/v0_1_17_to_v0_1_18 when the template file changes",
                )

    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.18", text)
        self.assertIn("script: migrations/v0_1_17_to_v0_1_18.py", text)

    def test_chains_from_every_older_version_reach_0_1_18(self) -> None:
        sync = load(SYNC_PATH, "sync_for_0_1_18")
        manifest = sync.parse_manifest(ROOT / ".template_sync/manifest.yaml")
        for start in ("0.0.0", "0.1.9", "0.1.14", "0.1.15", "0.1.16", "0.1.17"):
            chain = sync.resolve_migration_chain(manifest["migrations"], start, "0.1.18")
            self.assertEqual(chain[-1]["to"], "0.1.18", start)
        for entry in manifest["migrations"]:
            self.assertTrue((ROOT / ".template_sync" / entry["script"]).is_file(), entry["script"])

    def test_the_docs_are_linked_and_name_the_pinned_tag(self) -> None:
        self.assertIn("(migration_0_1_18.md)", (ROOT / ".tools/docs/README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / ".tools/docs/migration_0_1_18.md").is_file())
        bridge = (ROOT / ".tools/docs/tools_bridge.md").read_text(encoding="utf-8")
        self.assertIn(f"archive/refs/tags/{NEW_PIN}.zip", bridge)
        self.assertIn(f'LC_TOOLS_PIN="{NEW_PIN}"', bridge)
        self.assertNotIn(OLD_PIN, bridge)

    def test_the_template_scripts_pin_the_new_tag_once_per_script(self) -> None:
        for name in SCRIPT_NAMES:
            text = (ROOT / "app/bash_bat_scripts" / name).read_bytes().decode()
            with self.subTest(script=name):
                self.assertEqual(text.count(NEW_PIN), 1)
                self.assertNotIn(OLD_PIN, text)
                self.assertNotIn("refs/heads/", text)
        bat = (ROOT / "app/bash_bat_scripts/post_install.bat").read_bytes().decode()
        self.assertEqual(bat.count("\n"), bat.count("\r\n"), "post_install.bat must stay CRLF")

    def test_every_third_party_action_of_the_workflows_is_pinned_by_sha(self) -> None:
        files = sorted((ROOT / ".github/workflows").glob("*.y*ml")) + sorted((ROOT / ".template_sync/resources").glob("*/.github/workflows/*.y*ml"))
        self.assertGreaterEqual(len(files), 10)
        for path in files:
            lines = uses_lines(path)
            self.assertTrue(lines, path)
            for action, ref, tag in lines:
                with self.subTest(file=str(path.relative_to(ROOT)), action=action):
                    self.assertRegex(ref, r"^[0-9a-f]{40}$", "pin by the 40-character commit SHA")
                    self.assertIsNotNone(tag, "the tag stays as a comment")
                    self.assertEqual(PINS.get((action, tag or "")), ref, f"unknown pin for {action} {tag}")

    def test_the_tests_workflow_of_the_template(self) -> None:
        text = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^on:\n  pull_request:\n")
        self.assertRegex(text, r"(?m)^  push:\n    branches: \[main\]")
        self.assertNotIn("paths:", text, "the checks run for every change: no path filter")
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read\n")
        self.assertIn("github.repository == 'CellMigrationLab/LabConstrictor'", text, "it does not run in the apps created from the template")
        for command in ("pytest tests", "ruff check", "mypy .template_sync .tools/python tests"):
            self.assertIn(command, text)
        self.assertEqual(sum(1 for _ in uses_lines(ROOT / ".github/workflows/tests.yml")), 4, "two jobs, two actions each")
        self.assertIn("python tests/smoke/post_install_hosts.py", text, "the smoke install of post_install runs in CI")
        self.assertNotIn("LC_TOOLS_SPEC", text, "the smoke job installs the tag pinned by post_install: no Tools source override in CI")

    def test_the_install_rules_are_in_the_install_guide_with_one_wording(self) -> None:
        guide = (ROOT / ".tools/docs/install.md").read_text(encoding="utf-8")
        for rule in (RULE_PATH, RULE_UPDATE, RULE_LINUX):
            self.assertIn(rule, guide)
        markers = (("must contain no space", RULE_PATH), ("uninstalling the old version first", RULE_UPDATE), ("-u` updates in place", RULE_LINUX))
        docs = [*sorted((ROOT / ".tools/docs").glob("*.md")), ROOT / "README.md", *sorted((ROOT / ".tools/templates").glob("*.md"))]
        for path in docs:
            text = path.read_text(encoding="utf-8")
            for marker, rule in markers:
                if marker in text:
                    with self.subTest(doc=str(path.relative_to(ROOT)), rule=marker):
                        self.assertIn(rule, text, "a doc that states a rule uses the exact sentence of install.md")


class MigrationCase(unittest.TestCase):
    def setUp(self) -> None:
        self.migration = load(MIGRATION_PATH, "migration_0_1_18")
        self.helpers = self.migration._load_helpers()
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "app_repo"
        (self.repo / "app/bash_bat_scripts").mkdir(parents=True)
        (self.repo / "src/demoapp").mkdir(parents=True)
        (self.repo / "src/demoapp/__init__.py").write_text("", encoding="utf-8")
        (self.repo / "construct.yaml").write_text(CONSTRUCT, encoding="utf-8")
        (self.repo / ".tools/docs").mkdir(parents=True)
        (self.repo / ".github/workflows").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def script(self, name: str) -> Path:
        return self.repo / "app/bash_bat_scripts" / name

    def workflow(self, name: str) -> Path:
        return self.repo / ".github/workflows" / name

    def resource(self, relative: str) -> bytes:
        return (self.migration.RESOURCE_ROOT / relative).read_bytes()

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.migration.migrate(self.repo, {})
        return buffer.getvalue()

    def put_app(self, folder: Path, crlf_sh: bool = False) -> dict[str, bytes]:
        originals = {}
        for name in SCRIPT_NAMES:
            data = (folder / name).read_bytes()
            if crlf_sh and name.endswith(".sh"):
                data = to_crlf(data)
            self.script(name).write_bytes(data)
            originals[name] = data
        return originals


class PinTests(MigrationCase):
    APPS = ("playground", "nucleisky", "vlab4mic", "guessthecondition")

    def test_real_apps_move_to_the_new_pin_and_nothing_else_changes(self) -> None:
        for app in self.APPS:
            for crlf in (False, True):
                with self.subTest(app=app, crlf=crlf):
                    before = self.put_app(APPS_0_1_17 / app, crlf)
                    output = self.run_migration()
                    self.assertEqual(output.count(f"updated: Tools pin {OLD_PIN} -> {NEW_PIN}"), 2, output)
                    for name, data in before.items():
                        after = strip_hosts(name, self.script(name).read_bytes())
                        self.assertEqual(after, data.replace(OLD_PIN.encode(), NEW_PIN.encode()), name)
                        self.assertEqual(after.count(NEW_PIN.encode()), 1, name)
                        self.assertNotIn(OLD_PIN.encode(), after, name)
                        changed = [l for l in difflib.ndiff(data.decode().splitlines(), after.decode().splitlines()) if l[:2] in ("- ", "+ ")]
                        self.assertEqual(len(changed), 2, f"{name}: exactly the pin line changes, nothing else")
                    snap = pin_view(self.repo)
                    self.assertIn("no repository changes were required", self.run_migration())
                    self.assertEqual(pin_view(self.repo), snap, "second run: nothing changes")

    def test_the_new_template_scripts_of_the_apps_equal_the_live_template_after_the_move(self) -> None:
        """The scripts of an app are the template scripts with the app's names filled in: after the move they are the live template scripts."""
        for name in SCRIPT_NAMES:
            self.script(name).write_bytes((APPS_0_1_17 / "nucleisky" / name).read_bytes())
        self.run_migration()
        replacements = self.helpers.load_replacements(self.repo)
        replacements.update({"PROJECT_NAME": "NucleiSky", "PYTHON_PROJ_NAME": "nucleisky"})
        sh = self.script("post_install.sh").read_text(encoding="utf-8")
        live = self.helpers.render_template((ROOT / "app/bash_bat_scripts/post_install.sh").read_text(encoding="utf-8"), replacements, "\n")
        self.assertEqual(sh.count(f'LC_TOOLS_PIN="{NEW_PIN}"'), 1)
        self.assertIn(f'LC_TOOLS_PIN="{NEW_PIN}"', live)

    def test_an_app_with_its_own_pin_is_left_alone_with_a_note(self) -> None:
        for name in SCRIPT_NAMES:
            data = (APPS_0_1_17 / "nucleisky" / name).read_bytes().replace(OLD_PIN.encode(), b"v0.2.0-rc.2")
            self.script(name).write_bytes(data)
        before = pin_view(self.repo)
        output = self.run_migration()
        self.assertEqual(pin_view(self.repo), before)
        self.assertEqual(output.count("has its own pin v0.2.0-rc.2: left as it is"), 2, output)

    def test_unpinned_hooks_stay_as_they_are_with_a_note(self) -> None:
        for app in ("vlab4mic", "ns_pr32"):
            with self.subTest(app=app):
                self.put_app(BRIDGE_TEST / app)
                before = pin_view(self.repo)
                output = self.run_migration()
                self.assertEqual(pin_view(self.repo), before)
                self.assertEqual(output.count("has no LC_TOOLS_PIN line"), 2, output)

    def test_an_app_that_already_has_the_new_pin_is_unchanged(self) -> None:
        for name in SCRIPT_NAMES:
            self.script(name).write_bytes((APPS_0_1_17 / "nucleisky" / name).read_bytes().replace(OLD_PIN.encode(), NEW_PIN.encode()))
        before = pin_view(self.repo)
        output = self.run_migration()
        self.assertEqual(pin_view(self.repo), before)
        self.assertEqual(output.count(f"already pins Tools {NEW_PIN}: unchanged"), 2, output)

    def test_two_pin_lines_are_ambiguous_and_left_alone(self) -> None:
        sh = self.script("post_install.sh")
        text = (APPS_0_1_17 / "nucleisky/post_install.sh").read_text(encoding="utf-8")
        sh.write_text(text + f'\nLC_TOOLS_PIN="{OLD_PIN}"\n', encoding="utf-8")
        before = sh.read_bytes()
        output = self.run_migration()
        self.assertEqual(strip_hosts(sh.name, sh.read_bytes()), before)
        self.assertIn("has 2 LC_TOOLS_PIN lines", output)

    def test_only_the_exact_old_template_line_is_changed(self) -> None:
        sh = self.script("post_install.sh")
        text = (APPS_0_1_17 / "nucleisky/post_install.sh").read_text(encoding="utf-8")
        # the old value elsewhere (a comment, another variable) is not a pin line and stays; the pin line keeps its indent and trailing comment
        text = text.replace(f'LC_TOOLS_PIN="{OLD_PIN}"', f'LC_TOOLS_PIN="{OLD_PIN}"  # my comment') + f'# was {OLD_PIN}\nMY_VAR="{OLD_PIN}"\n'
        sh.write_text(text, encoding="utf-8")
        self.run_migration()
        after = strip_hosts(sh.name, sh.read_bytes()).decode()
        self.assertIn(f'LC_TOOLS_PIN="{NEW_PIN}"  # my comment', after)
        self.assertIn(f"# was {OLD_PIN}\n", after)
        self.assertIn(f'MY_VAR="{OLD_PIN}"\n', after)

    def test_scripts_without_the_hook_and_missing_files_are_not_touched_or_created(self) -> None:
        output = self.run_migration()
        self.assertEqual([p.name for p in (self.repo / "app/bash_bat_scripts").iterdir()], [])
        self.assertEqual(output.count("SKIPPED, file not found"), 2)
        self.script("post_install.sh").write_text('#!/bin/bash\necho mine\nLC_TOOLS_PIN="v0.2.0-rc.1"\n', encoding="utf-8")
        self.script("post_install.bat").write_bytes(b'@ECHO OFF\r\nSET "LC_TOOLS_PIN=v0.2.0-rc.1"\r\nEXIT /B 0\r\n')
        before = pin_view(self.repo)
        output = self.run_migration()
        self.assertEqual(pin_view(self.repo), before)
        self.assertEqual(output.count("nothing to move"), 2)


class WorkflowTests(MigrationCase):
    def test_a_workflow_identical_to_the_previous_template_version_gets_the_pinned_file(self) -> None:
        for crlf in (False, True):
            for name in WORKFLOW_NAMES:
                with self.subTest(workflow=name, crlf=crlf):
                    old = (WORKFLOWS_0_1_17 / name).read_bytes()
                    old = to_crlf(old) if crlf else to_lf(old) if name != "update_on_src_change.yaml" else old
                    self.workflow(name).write_bytes(old)
                    output = self.run_migration()
                    self.assertIn(f".github/workflows/{name}: updated: every third-party action is pinned by commit SHA", output)
                    expected = self.resource(f".github/workflows/{name}")
                    expected = to_crlf(expected) if b"\r\n" in old else to_lf(expected)
                    self.assertEqual(self.workflow(name).read_bytes(), expected, "pinned, line endings kept")
                    # only `uses:` lines differ from the previous version
                    changed = [l for l in difflib.ndiff(to_lf(old).decode().splitlines(), to_lf(self.workflow(name).read_bytes()).decode().splitlines()) if l[:2] in ("- ", "+ ")]
                    self.assertTrue(changed and all("uses:" in l for l in changed), changed)
                    self.workflow(name).unlink()

    def test_all_five_in_one_run_and_the_second_run_changes_nothing(self) -> None:
        for name in WORKFLOW_NAMES:
            self.workflow(name).write_bytes((WORKFLOWS_0_1_17 / name).read_bytes())
        output = self.run_migration()
        self.assertEqual(output.count("every third-party action is pinned by commit SHA"), 5, output)
        snap = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), snap)
        self.assertEqual(output.count("already the pinned template file: unchanged"), 5, output)
        self.assertIn("no repository changes were required", output)

    def test_workflows_the_apps_pinned_themselves_are_unchanged(self) -> None:
        """The apps pinned the actions by their own pull requests (same SHAs): their files equal the resources and are left alone."""
        for name in WORKFLOW_NAMES:
            self.workflow(name).write_bytes(self.resource(f".github/workflows/{name}"))
        before = snapshot(self.repo)
        output = self.run_migration()
        self.assertEqual(snapshot(self.repo), before)
        self.assertEqual(output.count("already the pinned template file: unchanged"), 5, output)

    def test_a_customised_and_already_pinned_workflow_is_left_alone(self) -> None:
        """Playground: release_constructor.yml without the Intel Mac build, pinned by the app."""
        target = self.workflow("release_constructor.yml")
        target.write_bytes((APPS_0_1_17 / "playground/release_constructor.yml").read_bytes())
        before = target.read_bytes()
        self.assertNotEqual(before, self.resource(".github/workflows/release_constructor.yml"))
        output = self.run_migration()
        self.assertEqual(target.read_bytes(), before)
        self.assertIn("release_constructor.yml: customised and already pinned: left as it is", output)

    def test_a_customised_unpinned_workflow_is_skipped_and_the_unpinned_actions_are_listed(self) -> None:
        target = self.workflow("update_on_notebook_change.yml")
        target.write_text((WORKFLOWS_0_1_17 / "update_on_notebook_change.yml").read_text(encoding="utf-8") + "# my own addition\n", encoding="utf-8")
        before = target.read_bytes()
        output = self.run_migration()
        self.assertEqual(target.read_bytes(), before)
        self.assertIn("update_on_notebook_change.yml: SKIPPED: customised", output)
        self.assertIn("tj-actions/changed-files@v44", output)
        self.assertIn("migration_0_1_18.md", output)

    def test_a_workflow_pinned_in_part_by_the_app_is_customised_and_skipped(self) -> None:
        target = self.workflow("sync_template.yml")
        text = (WORKFLOWS_0_1_17 / "sync_template.yml").read_text(encoding="utf-8")
        text = text.replace("actions/checkout@v4", "actions/checkout@" + PINS[("actions/checkout", "v4")] + " # v4")
        target.write_text(text, encoding="utf-8")
        before = target.read_bytes()
        output = self.run_migration()
        self.assertEqual(target.read_bytes(), before)
        self.assertIn("sync_template.yml: SKIPPED: customised", output)
        self.assertIn("peter-evans/create-pull-request@v6", output)

    def test_missing_workflows_are_not_created(self) -> None:
        output = self.run_migration()
        self.assertEqual(list((self.repo / ".github/workflows").iterdir()), [])
        self.assertEqual(output.count("not present in this repository (nothing was created)"), 5 + 2, output)  # five workflows, install.md, tools_bridge.md


class DocsTests(MigrationCase):
    def test_the_install_guide_of_0_1_17_gets_both_sections_and_nothing_is_removed(self) -> None:
        for crlf in (False, True):
            with self.subTest(crlf=crlf):
                old = (DOCS_0_1_17 / "install.md").read_bytes()
                old = to_crlf(old) if crlf else old
                target = self.repo / ".tools/docs/install.md"
                target.write_bytes(old)
                output = self.run_migration()
                self.assertIn("install.md: updated: added 'Before you install' and 'Update an installed app'", output)
                expected = self.resource(".tools/docs/install.md")
                self.assertEqual(target.read_bytes(), to_crlf(expected) if crlf else expected)
                removed = [l for l in difflib.ndiff(to_lf(old).decode().splitlines(), to_lf(target.read_bytes()).decode().splitlines()) if l.startswith("- ")]
                self.assertEqual(removed, [], "nothing is deleted")
                snap = snapshot(self.repo)
                self.assertIn("install.md: already has the install rules: unchanged", self.run_migration())
                self.assertEqual(snapshot(self.repo), snap)

    def test_a_customised_install_guide_gets_only_the_missing_section(self) -> None:
        target = self.repo / ".tools/docs/install.md"
        text = (DOCS_0_1_17 / "install.md").read_text(encoding="utf-8").replace("## Install on Windows", "## Install on Windows (my wording)")
        target.write_text(text, encoding="utf-8")
        output = self.run_migration()
        self.assertIn("SKIPPED: no line '## Install on Windows' to insert '## Before you install' before", output)
        self.assertEqual(target.read_text(encoding="utf-8"), text, "a step that cannot be done changes nothing in that file")

    def test_the_rules_are_in_the_inserted_text_word_for_word(self) -> None:
        target = self.repo / ".tools/docs/install.md"
        target.write_bytes((DOCS_0_1_17 / "install.md").read_bytes())
        self.run_migration()
        text = target.read_text(encoding="utf-8")
        for rule in (RULE_PATH, RULE_UPDATE, RULE_LINUX):
            self.assertIn(rule, text)

    def test_the_tools_guide_is_refreshed_only_if_it_is_the_0_1_17_text(self) -> None:
        target = self.repo / ".tools/docs/tools_bridge.md"
        target.write_bytes((DOCS_0_1_17 / "tools_bridge.md").read_bytes())
        self.assertIn(OLD_PIN, target.read_text(encoding="utf-8"))
        self.assertIn("tools_bridge.md: updated: written", self.run_migration())
        self.assertEqual(target.read_bytes(), self.resource(".tools/docs/tools_bridge.md"))
        self.assertIn("tools_bridge.md: unchanged", self.run_migration())
        custom = (DOCS_0_1_17 / "tools_bridge.md").read_text(encoding="utf-8") + "\nOur own note.\n"
        target.write_text(custom, encoding="utf-8")
        output = self.run_migration()
        self.assertIn("tools_bridge.md: SKIPPED: not the 0.1.17 text", output)
        self.assertEqual(target.read_text(encoding="utf-8"), custom)


class ChainTests(MigrationCase):
    def sync(self, start: str, end: str = "0.1.18") -> subprocess.CompletedProcess[str]:
        shutil.copytree(ROOT / ".template_sync", self.repo / ".template_sync", dirs_exist_ok=True)
        return subprocess.run(
            [sys.executable, str(self.repo / ".template_sync/sync.py"), "--from-version", start, "--to-version", end, "--repository-root", str(self.repo)],
            capture_output=True,
            text=True,
        )

    def test_the_sync_script_runs_the_migration_from_0_1_17(self) -> None:
        self.put_app(APPS_0_1_17 / "playground")
        for name in WORKFLOW_NAMES:
            self.workflow(name).write_bytes((WORKFLOWS_0_1_17 / name).read_bytes())
        result = self.sync("0.1.17")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[migration 0.1.18]", result.stdout)
        for name in WORKFLOW_NAMES:
            self.assertEqual(to_lf(self.workflow(name).read_bytes()), to_lf(self.resource(f".github/workflows/{name}")), name)
        self.assertIn(NEW_PIN.encode(), self.script("post_install.sh").read_bytes())
        again = self.sync("0.1.17")
        self.assertIn("no repository changes were required", again.stdout)

    def test_the_whole_chain_from_0_1_15_reaches_the_live_template_scripts(self) -> None:
        for name in (*SCRIPT_NAMES, "pre_uninstall.sh", "pre_uninstall.bat", "uninstall.sh"):
            source = self.helpers.read_text(OLD_SCRIPTS / name)
            replacements = self.helpers.load_replacements(self.repo)
            newline = "\r\n" if "\r\n" in source else "\n"
            self.script(name).write_bytes(self.helpers.render_template(source, replacements, newline).encode())
        result = self.sync("0.1.15")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        replacements = self.helpers.load_replacements(self.repo)
        for name in SCRIPT_NAMES:
            source = self.helpers.read_text(ROOT / "app/bash_bat_scripts" / name)
            newline = "\r\n" if "\r\n" in source else "\n"
            self.assertEqual(self.script(name).read_bytes(), self.helpers.render_template(source, replacements, newline).encode(), name)

    def test_a_hand_integrated_unpinned_app_ends_at_the_new_pin_through_the_chain(self) -> None:
        """VLab4Mic and NucleiSky pull request 32: unpinned source; 0.1.16 pins it to the then-template tag, 0.1.18 moves that tag."""
        for app in ("vlab4mic", "ns_pr32"):
            with self.subTest(app=app):
                self.put_app(BRIDGE_TEST / app)
                result = self.sync("0.1.15")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"Tools pin {OLD_PIN} -> {NEW_PIN}", result.stdout)
                for name in SCRIPT_NAMES:
                    data = self.script(name).read_bytes()
                    self.assertEqual(data.count(NEW_PIN.encode()), 1, name)
                    self.assertNotIn(OLD_PIN.encode(), data, name)
                    self.assertNotIn(b"refs/heads/", data, name)

    @unittest.skipUnless(shutil.which("bash"), "bash is not available")
    def test_migrated_bash_scripts_of_real_apps_have_valid_syntax_and_pin_the_new_tag_in_the_download_url(self) -> None:
        for app in PinTests.APPS:
            with self.subTest(app=app):
                self.put_app(APPS_0_1_17 / app)
                self.run_migration()
                path = self.script("post_install.sh")
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('${LC_TOOLS_SPEC:-https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/${LC_TOOLS_PIN}.zip}', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
