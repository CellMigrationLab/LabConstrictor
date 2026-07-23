from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectRenderingTests(unittest.TestCase):
    def test_gpu_migration_uses_initialized_project_folder(self) -> None:
        migration = load_module(
            "migration_0_1_5", ".template_sync/migrations/v0_1_4_to_v0_1_5.py"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "app/bash_bat_scripts").mkdir(parents=True)
            (repo / "construct.yaml").write_text(
                "name: LabConstrictor_Demo\nextra_files:\n"
                "- requirements.txt: LabConstrictor_Demo/requirements.txt\n",
                encoding="utf-8",
            )
            bat = repo / "app/bash_bat_scripts/post_install.bat"
            bat.write_text(
                '@ECHO OFF\n'
                'echo Running post_install > "%PREFIX%\\menuinst_debug.log"\n'
                '"%PREFIX%\\python.exe" -m pip install -r "%PREFIX%\\LabConstrictor_Demo\\requirements.txt" >> "%PREFIX%\\menuinst_debug.log"\n'
                'echo Post-install completed!\n'
                'SetLocal EnableDelayedExpansion\n',
                encoding="utf-8",
            )
            sh = repo / "app/bash_bat_scripts/post_install.sh"
            sh.write_text(
                '#!/bin/bash\n'
                'echo "Running post_install" > "$PREFIX/menuinst_debug.log"\n'
                '"$PREFIX/bin/python" -m pip install -r "$PREFIX/LabConstrictor_Demo/requirements.txt" >> "$PREFIX/menuinst_debug.log"\n',
                encoding="utf-8",
            )

            self.assertTrue(migration.update_post_install_bat(repo))
            self.assertTrue(migration.update_post_install_sh(repo))

            bat_text = bat.read_text(encoding="utf-8")
            sh_text = sh.read_text(encoding="utf-8")
            self.assertIn(
                'GPU_REQUIREMENTS=%PREFIX%\\LabConstrictor_Demo\\requirements_gpu.txt',
                bat_text,
            )
            self.assertIn(
                'GPU_REQUIREMENTS="$PREFIX/LabConstrictor_Demo/requirements_gpu.txt"',
                sh_text,
            )
            self.assertNotIn("PROJECT_NAME", bat_text + sh_text)

            nvidia_migration = load_module(
                "migration_0_1_7",
                ".template_sync/migrations/v0_1_6_to_v0_1_7.py",
            )
            self.assertTrue(nvidia_migration.update_post_install_bat(repo))
            hardened_bat = bat.read_text(encoding="utf-8")
            self.assertIn("CALL :detect_nvidia_smi", hardened_bat)
            self.assertIn(
                "LabConstrictor_Demo\\requirements_gpu.txt", hardened_bat
            )

    def test_debug_constructor_migration_renders_project_folder(self) -> None:
        migration = load_module(
            "migration_0_1_6", ".template_sync/migrations/v0_1_5_to_v0_1_6.py"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / ".tools/python").mkdir(parents=True)
            (repo / "construct.yaml").write_text(
                "name: LabConstrictor_Demo\n", encoding="utf-8"
            )
            script = repo / ".tools/python/bump_constructor.py"
            script.write_text(
                '''import re
from pathlib import Path


def extract_project_folder(extra_files: list) -> str:
    return "LabConstrictor_Demo"


def ensure_requirements_in_extra_files(construct_data: dict):
    extra_files = construct_data.get("extra_files", [])
    if not any(isinstance(item, dict) and "requirements.txt" in item for item in extra_files):
        extra_files.append({"requirements.txt": "LabConstrictor_Demo/requirements.txt"})
    construct_data["extra_files"] = extra_files


def ensure_extra_files(construct_data: dict, notebooks_root: Path, src_root: Path) -> int:
    return 0, 0


def main():
    return None
''',
                encoding="utf-8",
            )

            self.assertTrue(migration.update_bump_constructor(repo))
            updated = script.read_text(encoding="utf-8")
            self.assertIn(
                '"LabConstrictor_Demo/requirements_gpu.txt"', updated
            )
            self.assertIn(
                'project_name = "LabConstrictor_Demo"', updated
            )
            self.assertNotIn("PROJECT_NAME", updated)
            compile(updated, str(script), "exec")


if __name__ == "__main__":
    unittest.main()
