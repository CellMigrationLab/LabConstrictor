"""Tests of the app-hosts step of the 0.1.18 migration: labconstrictor-app.yaml bundled by the installer, passed to `register --app-manifest`.

Real files of apps at template 0.1.17 (tests/fixtures/template_0_1_17_apps: scripts and construct.yaml of each app's main, 13-14 Oct 2026) and the
real manifests of the apps (tests/fixtures/manifests), plus a CellTracksColab-like app (hosts: [notebook]).
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import ModuleType

from _hosts import strip_hosts


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_17_to_v0_1_18.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
APPS = FIXTURES / "template_0_1_17_apps"
MANIFESTS = FIXTURES / "manifests"
SCRIPT_NAMES = ("post_install.sh", "post_install.bat")
MANIFEST_NAME = "labconstrictor-app.yaml"
ARG = "--app-manifest"
# app folder -> (manifest fixture, project folder of its extra_files)
REAL_APPS = {
    "playground": ("playground_labconstrictor-app.yaml", "LabConstrictorPlayground"),
    "nucleisky": ("nucleisky_labconstrictor-app.yaml", "NucleiSky"),
    "vlab4mic": ("vlab4mic_labconstrictor-app.yaml", "VLab4Mic"),
    "guessthecondition": ("guessthecondition_labconstrictor-app.yaml", "GuessTheCondition"),
}
NO_HOSTS_SENTENCE = "declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def to_crlf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


class HostsCase(unittest.TestCase):
    def setUp(self) -> None:
        self.migration = load(MIGRATION_PATH, "migration_0_1_18_hosts")
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "app_repo"
        (self.repo / "app/bash_bat_scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def script(self, name: str) -> Path:
        return self.repo / "app/bash_bat_scripts" / name

    def put_app(self, app: str, manifest: str | None, crlf_sh: bool = False) -> None:
        """An app repository as it is at 0.1.17: its scripts, its construct.yaml and (optionally) its labconstrictor-app.yaml."""
        for name in SCRIPT_NAMES:
            data = (APPS / app / name).read_bytes()
            self.script(name).write_bytes(to_crlf(data) if crlf_sh and name.endswith(".sh") else data)
        (self.repo / "construct.yaml").write_bytes((APPS / app / "construct.yaml").read_bytes())
        if manifest is not None:
            (self.repo / MANIFEST_NAME).write_bytes((MANIFESTS / manifest).read_bytes())

    def run_migration(self) -> str:
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.migration.migrate(self.repo, {})
        return buffer.getvalue()

    def hosts_of(self, manifest: str) -> str:
        match = re.search(r"(?m)^hosts:.*$", (MANIFESTS / manifest).read_text(encoding="utf-8"))
        assert match is not None
        return match.group(0)


class RealAppsTests(HostsCase):
    def test_the_installer_bundles_the_manifest_and_the_hook_passes_it(self) -> None:
        for app, (manifest, folder) in REAL_APPS.items():
            for crlf in (False, True):
                with self.subTest(app=app, crlf=crlf):
                    self.put_app(app, manifest, crlf)
                    before = {n: self.script(n).read_bytes() for n in SCRIPT_NAMES}
                    construct_before = (self.repo / "construct.yaml").read_bytes()
                    output = self.run_migration()
                    self.assertIn("construct.yaml: updated: extra_files bundles labconstrictor-app.yaml", output)
                    self.assertEqual(output.count("updated: the Tools hook passes --app-manifest"), 2, output)
                    construct = (self.repo / "construct.yaml").read_bytes()
                    added = [l for l in construct.decode().splitlines() if "labconstrictor-app.yaml" in l]
                    self.assertEqual(added, [f"- {MANIFEST_NAME}: {folder}/{MANIFEST_NAME}"])
                    self.assertEqual(len(construct.splitlines()), len(construct_before.splitlines()) + 1, "one line added, nothing else")
                    for name in SCRIPT_NAMES:
                        after = self.script(name).read_bytes()
                        self.assertIn(ARG.encode(), after)
                        # nothing but the hosts lines changed: without them (and with the pin moved) the script is what it was
                        self.assertEqual(strip_hosts(name, after), before[name].replace(b"v0.2.0-rc.1", b"v0.3.0-alpha.1"))
                    for name in SCRIPT_NAMES:
                        after = self.script(name).read_bytes()
                        self.assertEqual(b"\r\n" in after, b"\r\n" in before[name], f"{name}: line endings kept")
                        if b"\r\n" in after:
                            self.assertEqual(after.count(b"\n"), after.count(b"\r\n"), f"{name}: every line ends with CRLF")

    def test_the_migrated_scripts_name_the_app_in_the_sentence_and_are_valid_shell(self) -> None:
        for app, (manifest, _) in REAL_APPS.items():
            with self.subTest(app=app):
                self.put_app(app, manifest)
                self.run_migration()
                sh = self.script("post_install.sh")
                name = re.search(r'--name "([^"]+)"', sh.read_text(encoding="utf-8"))
                assert name is not None
                self.assertIn(f"'{name.group(1)}' {NO_HOSTS_SENTENCE}", sh.read_text(encoding="utf-8"))
                self.assertIn(f"'{name.group(1)}' {NO_HOSTS_SENTENCE}", self.script("post_install.bat").read_text(encoding="utf-8").replace("^", ""))
                subprocess.run(["bash", "-n", str(sh)], check=True)

    def test_a_second_run_changes_nothing(self) -> None:
        for app, (manifest, _) in REAL_APPS.items():
            with self.subTest(app=app):
                self.put_app(app, manifest)
                self.run_migration()
                snap = tree(self.repo)
                output = self.run_migration()
                self.assertEqual(tree(self.repo), snap)
                self.assertEqual(output.count("already passes the hosts of the app to Tools: unchanged"), 2, output)
                self.assertIn("construct.yaml: already bundles labconstrictor-app.yaml: unchanged", output)

    def test_the_manifest_hosts_line_is_the_one_the_fixtures_declare(self) -> None:
        """The matrix of the apps (a guard on the fixtures the other tests rely on): the hosts line of each real manifest."""
        expected = {
            "playground": "hosts: [notebook, napari, fiji, qupath]",
            "vlab4mic": "hosts: [notebook, napari, fiji]",
            "celltrackscolab": "hosts: [notebook]",
        }
        for app, line in expected.items():
            self.assertEqual(self.hosts_of(f"{app}_labconstrictor-app.yaml"), line, app)

    def test_a_celltrackscolab_like_app_with_hosts_notebook_only(self) -> None:
        self.put_app("nucleisky", "celltrackscolab_labconstrictor-app.yaml")
        output = self.run_migration()
        self.assertIn("construct.yaml: updated: extra_files bundles labconstrictor-app.yaml", output)
        self.assertIn(f"- {MANIFEST_NAME}: NucleiSky/{MANIFEST_NAME}", (self.repo / "construct.yaml").read_text(encoding="utf-8"))
        self.assertIn(ARG, self.script("post_install.sh").read_text(encoding="utf-8"))


class SafetyTests(HostsCase):
    def test_without_a_manifest_construct_is_skipped_with_a_note_and_the_hook_still_logs(self) -> None:
        self.put_app("vlab4mic", None)
        construct = (self.repo / "construct.yaml").read_bytes()
        output = self.run_migration()
        self.assertEqual((self.repo / "construct.yaml").read_bytes(), construct)
        self.assertRegex(output, r"construct\.yaml: SKIPPED: the repository has no labconstrictor-app\.yaml, so it is not bundled")
        self.assertIn(ARG, self.script("post_install.sh").read_text(encoding="utf-8"), "the hook logs the missing file at install time")

    def test_nothing_is_ever_created_or_deleted(self) -> None:
        self.put_app("guessthecondition", "guessthecondition_labconstrictor-app.yaml")
        before = set(tree(self.repo))
        self.run_migration()
        self.assertEqual(set(tree(self.repo)), before)
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        with redirect_stdout(StringIO()):
            self.migration.migrate(empty, {})
        self.assertEqual(list(empty.iterdir()), [])

    def test_unknown_shapes_are_skipped_with_a_note_and_left_unchanged(self) -> None:
        self.put_app("nucleisky", "nucleisky_labconstrictor-app.yaml")
        flow = "name: X\nversion: 1\nextra_files: [a, b]\n"
        (self.repo / "construct.yaml").write_text(flow, encoding="utf-8")
        sh = self.script("post_install.sh")
        sh.write_text(sh.read_text(encoding="utf-8").replace("lc_note()", "my_note()"), encoding="utf-8")
        bat = self.script("post_install.bat")
        bat.write_bytes(bat.read_bytes().replace(b"IF NOT ERRORLEVEL 1 \"%PYTHON_EXE%\" -m labconstrictor_tools register", b"CALL \"%PYTHON_EXE%\" -m labconstrictor_tools register"))
        before = tree(self.repo)
        output = self.run_migration()
        self.assertEqual(tree(self.repo)["construct.yaml"], before["construct.yaml"])
        self.assertRegex(output, r"construct\.yaml: SKIPPED: expected one `extra_files:` block")
        self.assertRegex(output, r"post_install\.sh: SKIPPED: lc_note is not defined before the register line")
        self.assertRegex(output, r"post_install\.bat: SKIPPED: the register line does not have the known shape")
        self.assertNotIn(ARG, sh.read_text(encoding="utf-8"))
        self.assertNotIn(ARG, bat.read_text(encoding="utf-8"))

    def test_a_hook_that_registers_with_its_own_hosts_is_left_alone(self) -> None:
        self.put_app("nucleisky", "nucleisky_labconstrictor-app.yaml")
        sh = self.script("post_install.sh")
        sh.write_text(sh.read_text(encoding="utf-8").replace('--display-name "NucleiSky"', '--display-name "NucleiSky" --hosts notebook'), encoding="utf-8")
        before = sh.read_bytes()
        output = self.run_migration()
        self.assertEqual(sh.read_bytes().replace(b"v0.2.0-rc.1", b"v0.3.0-alpha.1"), before.replace(b"v0.2.0-rc.1", b"v0.3.0-alpha.1"))
        self.assertIn("post_install.sh: already passes the hosts of the app to Tools: unchanged", output)

    def test_a_mapping_that_exists_is_not_added_twice(self) -> None:
        self.put_app("nucleisky", "nucleisky_labconstrictor-app.yaml")
        construct = self.repo / "construct.yaml"
        construct.write_text(construct.read_text(encoding="utf-8").replace("extra_files:\n", f"extra_files:\n- {MANIFEST_NAME}: Mine/{MANIFEST_NAME}\n", 1), encoding="utf-8")
        before = construct.read_bytes()
        output = self.run_migration()
        self.assertEqual(construct.read_bytes(), before)
        self.assertIn("construct.yaml: already bundles labconstrictor-app.yaml: unchanged", output)

    def test_the_hand_integrated_hooks_of_vlab4mic_and_nucleisky_pr32_get_the_argument(self) -> None:
        for app in ("vlab4mic", "ns_pr32"):
            with self.subTest(app=app):
                for name in SCRIPT_NAMES:
                    self.script(name).write_bytes((FIXTURES / "bridge_test_hooks" / app / name).read_bytes())
                (self.repo / "construct.yaml").write_text("name: X\nextra_files:\n- a/Welcome.ipynb: X/Welcome.ipynb\n", encoding="utf-8")
                self.run_migration()
                for name in SCRIPT_NAMES:
                    self.assertIn(ARG, self.script(name).read_text(encoding="utf-8"), name)
                subprocess.run(["bash", "-n", str(self.script("post_install.sh"))], check=True)


if __name__ == "__main__":
    unittest.main()
