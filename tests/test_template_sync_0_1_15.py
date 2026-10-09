from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_14_to_v0_1_15.py"
CHECK_PATH = ROOT / ".tools/python/check_app_manifest.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.migration = load_module(MIGRATION_PATH, "migration_0_1_15")

    def test_resources_are_identical_to_the_template_files(self) -> None:
        for relative in self.migration.MANAGED_FILES:
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    (self.migration.RESOURCE_ROOT / relative).read_bytes(),
                    (ROOT / relative).read_bytes(),
                    "update .template_sync/resources/v0_1_14_to_v0_1_15 when the template file changes",
                )

    def test_migration_adds_the_check_and_leaves_the_app_manifest_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            manifest = repo / "labconstrictor-app.yaml"
            manifest.write_text("schema: 1\n# written by the app's author\n", encoding="utf-8")
            self.migration.migrate(repo_root=repo, context={})
            self.migration.migrate(repo_root=repo, context={})  # running it twice changes nothing
            for relative in self.migration.MANAGED_FILES:
                self.assertTrue((repo / relative).is_file(), relative)
            self.assertEqual(manifest.read_text(encoding="utf-8"), "schema: 1\n# written by the app's author\n")

    def test_the_manifest_lists_the_migration_and_the_new_version(self) -> None:
        text = (ROOT / ".template_sync/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("template_version: 0.1.15", text)
        self.assertIn("script: migrations/v0_1_14_to_v0_1_15.py", text)


class CheckScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.check = load_module(CHECK_PATH, "check_app_manifest")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".tools/schema").mkdir(parents=True)
        (self.root / ".tools/schema/labconstrictor-app.schema.json").write_bytes(
            (ROOT / ".tools/schema/labconstrictor-app.schema.json").read_bytes()
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, text: str) -> None:
        (self.root / "labconstrictor-app.yaml").write_text(text, encoding="utf-8")

    VALID = (
        "schema: 1\nname: Cool Analytics\nsummary: Count and track cells in time-lapse movies.\n"
        "kind: analysis\ndistribution:\n  installer: true\n"
    )

    def test_a_valid_manifest_passes(self) -> None:
        self.write(self.VALID)
        self.assertEqual(self.check.check(self.root), 0)

    def test_a_missing_manifest_warns_and_passes(self) -> None:
        self.assertEqual(self.check.check(self.root), 0)

    def test_an_invalid_manifest_fails(self) -> None:
        self.write(self.VALID.replace("kind: analysis", "kind: magic"))
        self.assertEqual(self.check.check(self.root), 1)

    def test_invalid_yaml_fails(self) -> None:
        self.write("schema: 1\nname: [unclosed\n")
        self.assertEqual(self.check.check(self.root), 1)

    def test_a_named_icon_must_exist(self) -> None:
        self.write(self.VALID + "icon: app/logo/missing.png\n")
        self.assertEqual(self.check.check(self.root), 1)
        (self.root / "app/logo").mkdir(parents=True)
        (self.root / "app/logo/missing.png").write_bytes(b"\x89PNG")
        self.assertEqual(self.check.check(self.root), 0)

    def test_a_missing_schema_copy_raises_instead_of_passing(self) -> None:
        (self.root / ".tools/schema/labconstrictor-app.schema.json").unlink()
        self.write(self.VALID)
        with self.assertRaises(self.check.CheckError):
            self.check.check(self.root)


if __name__ == "__main__":
    unittest.main()
