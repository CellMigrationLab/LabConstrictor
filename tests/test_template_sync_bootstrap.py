from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC_PATH = ROOT / ".template_sync" / "sync.py"
MANIFEST_PATH = ROOT / ".template_sync" / "manifest.yaml"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("template_sync", SYNC_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SYNC_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateSyncBootstrapTests(unittest.TestCase):
    def test_first_time_repository_resolves_to_latest_template(self) -> None:
        sync = load_sync_module()
        manifest = sync.parse_manifest(MANIFEST_PATH)

        chain = sync.resolve_migration_chain(
            manifest["migrations"],
            from_version="0.0.0",
            to_version=manifest["template_version"],
        )

        self.assertTrue(chain)
        self.assertEqual(chain[0]["from"], "0.0.0")
        self.assertEqual(chain[0]["to"], "0.0.1")
        self.assertEqual(chain[-1]["to"], manifest["template_version"])

    def test_bootstrap_migration_script_exists(self) -> None:
        sync = load_sync_module()
        manifest = sync.parse_manifest(MANIFEST_PATH)
        bootstrap = next(
            migration
            for migration in manifest["migrations"]
            if migration["from"] == "0.0.0"
        )

        self.assertTrue((ROOT / ".template_sync" / bootstrap["script"]).is_file())


if __name__ == "__main__":
    unittest.main()
