from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_migration(version: str):
    path = ROOT / ".template_sync/migrations" / version
    spec = importlib.util.spec_from_file_location(version.replace(".", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EARLY_CONSTRUCTOR = '''import re
from pathlib import Path


def extract_project_folder(extra_files: list) -> str:
    return "LabConstrictor_Demo"


def ensure_requirements_in_extra_files(construct_data: dict):
    extra_files = construct_data.get("extra_files")
    if extra_files is None:
        extra_files = []
        construct_data["extra_files"] = extra_files

    requirements_included = any(
        isinstance(item, dict) and "requirements.txt" in item for item in extra_files
    )
    if not requirements_included:
        extra_files.append({"requirements.txt": "LabConstrictor_Demo/requirements.txt"})

    if Path("requirements-linux.txt").exists():
        pass

    construct_data["extra_files"] = extra_files


def ensure_extra_files(construct_data: dict, notebooks_root: Path, src_root: Path) -> int:
    extra_files = construct_data.get("extra_files", [])
    project_folder = extract_project_folder(extra_files)
    existing_sources = set()
    existing_dests = set()
    normalized_items = []
    repo_root = Path(".").resolve()
    src_added = 0
    included_src_flag = False
    for py_file in src_root.rglob("*.py"):
        rel = py_file.relative_to(repo_root).as_posix()
        if not rel.startswith("src/"):
            continue
        src = rel
        project_name = "labconstrictor_demo"
        dst = f"{project_folder}/src/{project_name}/{rel.replace('src/', '')}"

        normalized_items.append({src: dst})
        included_src_flag = True
        src_added += 1

    if included_src_flag:
        setup_src = "setup.py"
        setup_dst = f"{project_folder}/setup.py"
        if setup_src not in existing_sources and setup_dst not in existing_dests:
            normalized_items.append({setup_src: setup_dst})
            src_added += 1

        src_change_file = ".tools/meta/src_change.yaml"
        if Path(src_change_file).exists():
            src_change_dst = f"{project_folder}/src_change.yaml"
            if src_change_file not in existing_sources and src_change_dst not in existing_dests:
                normalized_items.append({src_change_file: src_change_dst})
                src_added += 1

    # Optionally sort entries (dicts by their single key) for determinism
    def sort_key(item):
        return str(item)

    normalized_items.sort(key=sort_key)
    construct_data["extra_files"] = normalized_items
    return 0, src_added


def main():
    return None
'''


EARLY_BUMP_VERSION = '''#!/usr/bin/env python3
import argparse
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONSTRUCT = ROOT / "construct.yaml"
VERSION_LINE_RE = re.compile(r"^(version:)(.*)$", re.MULTILINE)
THANKS_LINE_RE = re.compile(r'(Thank you! You have successfully installed [^\\n]*)(\\d+\\.\\d+\\.\\d+)(!)')
POST_INSTALL = ROOT / "app" / "bash_bat_scripts" / "post_install.bat"


def replace_version_in_file(file_path: pathlib.Path, old_version: str, new_version: str) -> bool:
    return False


def read_current_version() -> tuple[str, str]:
    return "version: 0.0.0", "0.0.0"


def bump_construct_text(text: str, old_version: str, new_version: str) -> str:
    def _repl_version(m: re.Match) -> str:
        return new_version
    text = VERSION_LINE_RE.sub(_repl_version, text, count=1)
    text = THANKS_LINE_RE.sub(lambda m: f"{m.group(1)}{new_version}{m.group(3)}", text, count=1)
    return text


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


class ToolMigrationChainTests(unittest.TestCase):
    def test_initialized_tool_scripts_reach_latest_shape(self) -> None:
        migrations = {
            "012": load_migration("v0_1_1_to_v0_1_2.py"),
            "014": load_migration("v0_1_3_to_v0_1_4.py"),
            "015": load_migration("v0_1_4_to_v0_1_5.py"),
            "016": load_migration("v0_1_5_to_v0_1_6.py"),
            "018": load_migration("v0_1_7_to_v0_1_8.py"),
            "019": load_migration("v0_1_8_to_v0_1_9.py"),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            tools = repo / ".tools/python"
            tools.mkdir(parents=True)
            constructor = tools / "bump_constructor.py"
            bump_version = tools / "bump_version.py"
            constructor.write_text(EARLY_CONSTRUCTOR, encoding="utf-8")
            bump_version.write_text(EARLY_BUMP_VERSION, encoding="utf-8")
            (repo / "construct.yaml").write_text(
                "name: LabConstrictor_Demo\n", encoding="utf-8"
            )

            self.assertTrue(migrations["012"].update_bump_constructor(repo))
            self.assertTrue(migrations["014"].update_bump_constructor(repo))
            self.assertTrue(migrations["014"].update_bump_version(repo))
            self.assertTrue(migrations["015"].update_bump_constructor(repo))
            self.assertTrue(migrations["016"].update_bump_constructor(repo))
            self.assertTrue(migrations["016"].update_bump_version(repo))
            self.assertTrue(migrations["018"].update_bump_version(repo))
            self.assertTrue(migrations["018"].update_bump_constructor(repo))
            self.assertTrue(migrations["019"].update_bump_constructor(repo))

            constructor_text = constructor.read_text(encoding="utf-8")
            bump_version_text = bump_version.read_text(encoding="utf-8")
            self.assertNotIn("PROJECT_NAME", constructor_text)
            self.assertIn("LabConstrictor_Demo/requirements.txt", constructor_text)
            self.assertIn("only_init_files = True", constructor_text)
            self.assertIn("possible_download_md_paths", bump_version_text)
            self.assertIn("bare_body", bump_version_text)
            compile(constructor_text, str(constructor), "exec")
            compile(bump_version_text, str(bump_version), "exec")


if __name__ == "__main__":
    unittest.main()
