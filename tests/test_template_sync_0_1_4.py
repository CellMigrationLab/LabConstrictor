from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_3_to_v0_1_4.py"


def load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0_1_4", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EARLY_BUMP_VERSION = '''#!/usr/bin/env python3
import argparse
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONSTRUCT = ROOT / "construct.yaml"
POST_INSTALL = ROOT / "app" / "bash_bat_scripts" / "post_install.bat"


def read_current_version() -> tuple[str, str]:
    return "version: 0.0.0", "0.0.0"


def bump_construct_text(text: str, old_version: str, new_version: str) -> str:
    return text.replace(old_version, new_version)


def bump_post_install_bat(new_version: str) -> None:
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("new_version")
    args = parser.parse_args()

    if not re.fullmatch(r"\\d+\\.\\d+\\.\\d+", args.new_version):
        sys.exit("Version must look like X.Y.Z")

    # On the first release replace download_executable.md with the template
    # (but only if it exists)
    if pathlib.Path(".tools/templates/download_executable_template.md").exists():
        # Remove existing download_executable.md if present
        if pathlib.Path(".tools/docs/download_executable.md").exists():
            pathlib.Path(".tools/docs/download_executable.md").unlink()
        # Copy the template to the docs folder using shutil for cross-platform support
        shutil.copy(
            ".tools/templates/download_executable_template.md",
            ".tools/docs/download_executable.md",
        )

    text, current = read_current_version()
    updated_text = bump_construct_text(text, current, args.new_version)

    # Also bump PKG_VERSION in post_install.bat
    bump_post_install_bat(args.new_version)


if __name__ == "__main__":
    main()
'''


class TemplateSync014Tests(unittest.TestCase):
    def test_early_bump_version_without_helper_is_supported(self) -> None:
        migration = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            path = repo / ".tools/python/bump_version.py"
            path.parent.mkdir(parents=True)
            path.write_text(EARLY_BUMP_VERSION, encoding="utf-8")

            self.assertTrue(migration.update_bump_version(repo))
            updated = path.read_text(encoding="utf-8")
            self.assertIn(
                "def bump_version_in_download_executable_md(new_version: str)",
                updated,
            )
            self.assertIn(
                "bump_version_in_download_executable_md(args.new_version)",
                updated,
            )
            self.assertNotIn(
                'if pathlib.Path(".tools/templates/download_executable_template.md").exists():',
                updated,
            )
            compile(updated, str(path), "exec")
            self.assertFalse(migration.update_bump_version(repo))

    def test_newer_constructor_shape_is_accepted(self) -> None:
        migration = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            path = repo / ".tools/python/bump_constructor.py"
            path.parent.mkdir(parents=True)
            current = (ROOT / ".tools/python/bump_constructor.py").read_text(
                encoding="utf-8"
            )
            path.write_text(current, encoding="utf-8")

            self.assertFalse(migration.update_bump_constructor(repo))
            self.assertEqual(current, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
