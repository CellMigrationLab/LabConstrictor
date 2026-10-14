"""The live post_install.sh of the template passes the app's hosts to `labconstrictor-tools register` (and says so when it cannot).

The script runs for real (bash) in a fake install prefix whose "python" is a small shell stub that records the arguments of `register`: the
registry entry itself is checked by the smoke install of the template CI (tests/smoke/post_install_hosts.py, which needs Tools).
`bump_constructor.py` is tested here too: it bundles labconstrictor-app.yaml in extra_files only when the file exists.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app/bash_bat_scripts/post_install.sh"
BAT = ROOT / "app/bash_bat_scripts/post_install.bat"
NO_HOSTS = "'DemoApp' declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose"
STUB_PYTHON = """#!/bin/bash
# stands for the bundled python: records `register` calls, answers the module check with "found", does nothing else
case "$*" in
    *--print-ca-bundle*) echo "$STUB_CA" ;;
    *"-m labconstrictor_tools register"*) echo "$@" >> "$STUB_REGISTER_ARGS" ;;
esac
exit 0
"""


def render(text: str) -> str:
    for token, value in (("UNDERSCORED_PROJECT_NAME", "Demo_App"), ("PYTHON_PROJ_NAME", "demoapp"), ("PROJECT_NAME", "DemoApp")):
        text = text.replace(token, value)
    return text


class LiveScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.prefix = base / "prefix"
        self.root = self.prefix / "DemoApp"
        (self.prefix / "bin").mkdir(parents=True)
        self.root.mkdir()
        python = self.prefix / "bin/python"
        python.write_text(STUB_PYTHON, encoding="utf-8")
        python.chmod(python.stat().st_mode | stat.S_IEXEC)
        for name in ("launch_jupyter.py", "requirements.txt", "setup.py"):
            (self.root / name).write_text("", encoding="utf-8")
        (self.root / "construct.yaml").write_text("name: Demo_App\nversion: 1.2.3\n", encoding="utf-8")
        self.ca = base / "ca.pem"
        self.ca.write_text("ca", encoding="utf-8")
        self.recorded = base / "register_args.txt"
        self.script = base / "post_install.sh"
        self.script.write_text(render(SCRIPT.read_text(encoding="utf-8")), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install(self) -> str:
        env = {**os.environ, "PREFIX": str(self.prefix), "STUB_CA": str(self.ca), "STUB_REGISTER_ARGS": str(self.recorded)}
        subprocess.run(["bash", str(self.script)], check=True, env=env, stdin=subprocess.DEVNULL, capture_output=True)
        return (self.prefix / "menuinst_debug.log").read_text(encoding="utf-8")

    def registered(self) -> str:
        return self.recorded.read_text(encoding="utf-8").strip()

    def test_the_bundled_manifest_goes_to_register(self) -> None:
        manifest = self.root / "labconstrictor-app.yaml"
        manifest.write_text("schema: 1\nname: Demo\nhosts: [notebook, napari]\n", encoding="utf-8")
        log = self.install()
        self.assertTrue(self.registered().endswith(f"--app-manifest {manifest}"), self.registered())
        self.assertIn("--name DemoApp", self.registered())
        self.assertIn(f"Passing the hosts of {manifest} to Tools (--app-manifest).", log)
        self.assertNotIn("WARNING", log)

    def test_a_missing_manifest_is_logged_with_the_sentence_and_registers_without_hosts(self) -> None:
        log = self.install()
        self.assertNotIn("--app-manifest", self.registered())
        self.assertNotIn("--hosts", self.registered())
        self.assertIn(f"WARNING: {self.root}/labconstrictor-app.yaml was not found", log)
        self.assertIn("add labconstrictor-app.yaml to extra_files in construct.yaml", log)
        self.assertIn(NO_HOSTS, log)

    def test_a_manifest_without_a_hosts_line_is_logged_with_the_sentence_and_still_passed(self) -> None:
        manifest = self.root / "labconstrictor-app.yaml"
        manifest.write_text("schema: 1\nname: Demo\n", encoding="utf-8")
        log = self.install()
        self.assertIn(f"--app-manifest {manifest}", self.registered())
        self.assertIn(f"WARNING: {manifest} has no hosts: line", log)
        self.assertIn(NO_HOSTS, log)

    def test_a_manifest_with_crlf_and_a_spaced_hosts_key_counts_as_declared(self) -> None:
        manifest = self.root / "labconstrictor-app.yaml"
        manifest.write_bytes(b"schema: 1\r\nhosts : [notebook]\r\n")
        log = self.install()
        self.assertIn("Passing the hosts of", log)
        self.assertNotIn("WARNING", log)


class TemplateTextTests(unittest.TestCase):
    def test_the_bat_script_has_the_same_sentence_and_both_register_lines(self) -> None:
        text = BAT.read_text(encoding="utf-8").replace("^", "")
        self.assertEqual(text.count("'PROJECT_NAME' declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose"), 2)
        self.assertEqual(text.count('--app-manifest "%LC_APP_MANIFEST%"'), 1)
        self.assertEqual(text.count("labconstrictor_tools register"), 2)

    def test_the_sh_script_passes_the_argument_with_an_idiom_that_works_in_bash_3(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('${LC_HOSTS_ARGS[@]+"${LC_HOSTS_ARGS[@]}"}', text, "macOS bash 3.2 fails on an empty array under set -u without it")
        self.assertEqual(text.count("labconstrictor_tools register"), 1)


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BumpConstructorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bump = load(ROOT / ".tools/python/bump_constructor.py", "bump_constructor_hosts")
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = Path(self.tmp.name) / "labconstrictor-app.yaml"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def data() -> dict:
        return {"extra_files": [{"app/menuinst/Welcome.ipynb": "DemoApp/notebooks/Welcome.ipynb"}]}

    def test_the_mapping_is_added_when_the_file_exists_and_only_once(self) -> None:
        self.manifest.write_text("schema: 1\n", encoding="utf-8")
        data = self.data()
        self.assertTrue(self.bump.ensure_app_manifest_in_extra_files(data, self.manifest))
        self.assertIn({"labconstrictor-app.yaml": "DemoApp/labconstrictor-app.yaml"}, data["extra_files"])
        self.assertFalse(self.bump.ensure_app_manifest_in_extra_files(data, self.manifest))
        self.assertEqual(sum("labconstrictor-app.yaml" in item for item in data["extra_files"]), 1)

    def test_no_mapping_is_added_for_a_missing_file(self) -> None:
        data = self.data()
        self.assertFalse(self.bump.ensure_app_manifest_in_extra_files(data, self.manifest))
        self.assertEqual(data, self.data())

    def test_a_mapping_whose_file_is_gone_is_kept_and_reported(self) -> None:
        data = self.data()
        data["extra_files"].append({"labconstrictor-app.yaml": "Mine/labconstrictor-app.yaml"})
        from contextlib import redirect_stdout
        from io import StringIO

        out = StringIO()
        with redirect_stdout(out):
            self.assertFalse(self.bump.ensure_app_manifest_in_extra_files(data, self.manifest))
        self.assertIn("WARNING: extra_files maps labconstrictor-app.yaml but the file does not exist", out.getvalue())
        self.assertIn({"labconstrictor-app.yaml": "Mine/labconstrictor-app.yaml"}, data["extra_files"])


if __name__ == "__main__":
    unittest.main()
