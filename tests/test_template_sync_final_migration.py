from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_9_to_v0_1_10.py"


def load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0_1_10", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinalMigrationTests(unittest.TestCase):
    def test_initialized_demo_repository_reaches_tls_template(self) -> None:
        migration = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "app/bash_bat_scripts").mkdir(parents=True)
            (repo / "app/menuinst").mkdir(parents=True)
            (repo / "src/labconstrictor_demo").mkdir(parents=True)
            (repo / "src/labconstrictor_demo/__init__.py").write_text(
                "", encoding="utf-8"
            )
            (repo / "construct.yaml").write_text(
                """name: LabConstrictor_Demo
version: 0.0.1
icon_image: app/logo/logo.png
extra_files:
- app/menuinst/Welcome.ipynb: LabConstrictor_Demo/notebooks/Welcome.ipynb
- app/menuinst/notebook_launcher.json: LabConstrictor_Demo/notebook_launcher.json
- app/python_scripts/include_path.py: LabConstrictor_Demo/include_path.py
- requirements.txt: LabConstrictor_Demo/requirements.txt
post_install: app/bash_bat_scripts/post_install.bat # [win]
""",
                encoding="utf-8",
            )
            (repo / "environment.yaml").write_text(
                """name: labconstrictor_demo
channels:
- conda-forge
dependencies:
- python=3.11.13
- pip
- jupyterlab=4.4.0
""",
                encoding="utf-8",
            )
            (repo / "setup.py").write_text(
                'from setuptools import setup\nsetup(name="labconstrictor_demo")\n',
                encoding="utf-8",
            )
            (repo / "app/bash_bat_scripts/post_install.bat").write_text(
                'SET "PUBLISHER=CellMigrationLab"\n', encoding="utf-8"
            )
            (repo / "app/bash_bat_scripts/post_install.sh").write_text(
                "#!/bin/bash\n", encoding="utf-8"
            )
            launcher = {
                "menu_items": [
                    {
                        "platforms": {
                            "win": {
                                "icon": "BASE_PATH_KEYWORD/LabConstrictor_Demo/logo.ico"
                            },
                            "linux": {
                                "icon": "BASE_PATH_KEYWORD/LabConstrictor_Demo/logo.png"
                            },
                            "osx": {
                                "icon": "BASE_PATH_KEYWORD/LabConstrictor_Demo/logo.icns"
                            },
                        }
                    }
                ]
            }
            (repo / "app/menuinst/notebook_launcher.json").write_text(
                json.dumps(launcher), encoding="utf-8"
            )

            migration.migrate(repo, {})

            construct = (repo / "construct.yaml").read_text(encoding="utf-8")
            environment = (repo / "environment.yaml").read_text(encoding="utf-8")
            self.assertIn(
                "app/python_scripts/launch_jupyter.py: LabConstrictor_Demo/launch_jupyter.py",
                construct,
            )
            self.assertIn("pip>=24.2", environment)
            self.assertTrue((repo / "app/python_scripts/launch_jupyter.py").is_file())
            self.assertTrue((repo / ".tools/docs/troubleshooting.md").is_file())
            generated_bat = (repo / "app/bash_bat_scripts/post_install.bat").read_text(
                encoding="utf-8"
            )
            self.assertIn("LabConstrictor_Demo", generated_bat)
            self.assertIn("labconstrictor_demo", generated_bat)
            self.assertNotIn("PROJECT_NAME", generated_bat)
            self.assertNotIn("PYTHON_PROJ_NAME", generated_bat)


if __name__ == "__main__":
    unittest.main()
