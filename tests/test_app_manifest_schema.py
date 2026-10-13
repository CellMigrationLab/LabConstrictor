"""The vendored App Centre schema: real manifests pass, invented fields fail, and the copy cannot silently drift from the Site."""
from __future__ import annotations

import importlib.util
import os
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures/manifests"
SCHEMA = ROOT / ".tools/schema/labconstrictor-app.schema.json"
SITE_SCHEMA_URL = "https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor-Site/main/schema/labconstrictor-app.schema.json"


def load_check():
    spec = importlib.util.spec_from_file_location("check_app_manifest_schema_test", ROOT / ".tools/python/check_app_manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RealManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.check = load_check()
        self.schema = self.check.load_schema(ROOT)

    def problems(self, manifest) -> list[str]:
        return self.check.schema_problems(manifest, self.schema)

    def test_the_nucleisky_and_playground_manifests_are_valid(self) -> None:
        for name in ("nucleisky", "playground"):
            with self.subTest(app=name):
                manifest = yaml.safe_load((FIXTURES / f"{name}_labconstrictor-app.yaml").read_text(encoding="utf-8"))
                self.assertEqual(self.problems(manifest), [])

    def test_the_app_centre_fields_are_known(self) -> None:
        manifest = yaml.safe_load((FIXTURES / "nucleisky_labconstrictor-app.yaml").read_text(encoding="utf-8"))
        for field in ("inputs", "outputs", "limitations"):
            self.assertIn(field, manifest, f"the NucleiSky fixture should use {field}")

    def test_an_invented_field_still_fails(self) -> None:
        for name in ("nucleisky", "playground"):
            with self.subTest(app=name):
                manifest = yaml.safe_load((FIXTURES / f"{name}_labconstrictor-app.yaml").read_text(encoding="utf-8"))
                manifest["invented_field"] = "x"
                problems = self.problems(manifest)
                self.assertTrue(any("invented_field" in p for p in problems), problems)

    def test_bad_values_of_the_new_fields_fail(self) -> None:
        manifest = yaml.safe_load((FIXTURES / "nucleisky_labconstrictor-app.yaml").read_text(encoding="utf-8"))
        for field, value in (("limitations", []), ("outputs", ["x"]), ("inputs", ["fine text"] * 7), ("status", "Beta")):
            with self.subTest(field=field):
                self.assertTrue(self.problems({**manifest, field: value}))

    def test_platforms_need_an_installer(self) -> None:
        manifest = {"schema": 1, "name": "X App", "summary": "Counts cells in movies of time-lapse imaging.", "kind": "analysis",
                    "distribution": {"pip": "x-app", "platforms": ["linux-x86_64"]}}
        self.assertTrue(self.problems(manifest))
        manifest["distribution"] = {"installer": True, "platforms": ["linux-x86_64"]}
        self.assertEqual(self.problems(manifest), [])


class DriftGuardTests(unittest.TestCase):
    def test_the_template_copy_is_the_schema_of_the_site(self) -> None:
        """Fails when the copy is stale. The workflow check_schema_drift.yml sets LC_SCHEMA_DRIFT_REQUIRED=1 so that an unreachable Site is a failure there."""
        try:
            with urllib.request.urlopen(SITE_SCHEMA_URL, timeout=30) as response:
                site = response.read()
        except (urllib.error.URLError, OSError) as err:
            if os.environ.get("LC_SCHEMA_DRIFT_REQUIRED") == "1":
                self.fail(f"cannot fetch the Site schema: {err}")
            self.skipTest(f"offline, the Site schema was not compared ({err})")
        self.assertEqual(
            SCHEMA.read_bytes().replace(b"\r\n", b"\n"),
            site.replace(b"\r\n", b"\n"),
            "the schema copy differs from LabConstrictor-Site schema/labconstrictor-app.schema.json: copy it to .tools/schema/, "
            "to a new .template_sync/resources/ folder, and bump the template version (see .tools/schema/README.md)",
        )


if __name__ == "__main__":
    unittest.main()
