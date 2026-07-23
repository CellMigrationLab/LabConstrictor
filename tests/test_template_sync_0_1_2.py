from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / ".template_sync/migrations/v0_1_1_to_v0_1_2.py"


def load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0_1_2", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateSync012Tests(unittest.TestCase):
    def make_demo_fixture(self, root: Path) -> None:
        (root / ".tools/templates").mkdir(parents=True)
        (root / ".tools/docs").mkdir(parents=True)
        (root / "src/labconstrictor_demo").mkdir(parents=True)
        (root / "src/labconstrictor_demo/__init__.py").write_text("", encoding="utf-8")
        (root / "setup.py").write_text(
            'from setuptools import setup\nsetup(name="labconstrictor_demo", package_dir={"": "src"})\n',
            encoding="utf-8",
        )

        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "from pathlib import Path\n",
                        "        src_folder = Path(\"..\") / \"src\" / \"labconstrictor_demo\"\n",
                    ],
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        (root / ".tools/templates/Welcome_template.ipynb").write_text(
            json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )

        (root / ".tools/docs/external_code_upload.md").write_text(
            """# Adding External Code

```
src
|-- __init__.py
|-- my_script.py
|-- subpackage/
    |-- __init__.py
    |-- submodule1.py
```

```python
# src/__init__.py
```

```python
import labconstrictor_demo
```

```python
from labconstrictor_demo import subpackage
```
""",
            encoding="utf-8",
        )

    def test_customized_first_time_repository_migrates_without_placeholder(self) -> None:
        migration = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self.make_demo_fixture(repo)

            migration.migrate(repo_root=repo, context={})

            notebook = json.loads(
                (repo / ".tools/templates/Welcome_template.ipynb").read_text(
                    encoding="utf-8"
                )
            )
            source = "".join(notebook["cells"][0]["source"])
            self.assertIn('src_folder = Path("..") / "src"', source)
            self.assertNotIn('/ "labconstrictor_demo"', source)

            docs = (repo / ".tools/docs/external_code_upload.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("|-- labconstrictor_demo/", docs)
            self.assertIn("# src/labconstrictor_demo/__init__.py", docs)
            self.assertIn(
                "from labconstrictor_demo.subpackage import submodule1", docs
            )

    def test_migration_is_idempotent_for_customized_repository(self) -> None:
        migration = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self.make_demo_fixture(repo)
            migration.migrate(repo_root=repo, context={})

            before = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file()
            }
            migration.migrate(repo_root=repo, context={})
            after = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

class TemplateSync013NotebookTests(unittest.TestCase):
    def test_legacy_notebook_url_is_updated_semantically(self) -> None:
        migration_path = ROOT / ".template_sync/migrations/v0_1_2_to_v0_1_3.py"
        spec = importlib.util.spec_from_file_location("migration_0_1_3", migration_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {migration_path}")
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        old_url = (
            'f"https://api.github.com/repos/{github_owner}/{github_repo_name}'
            '/contents/notebooks/{main_folder}/{subfolder}/{subfolder}.ipynb'
            '?ref={github_branch}"'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            path = repo / ".tools/templates/Welcome_template.ipynb"
            path.parent.mkdir(parents=True)
            notebook = {
                "cells": [
                    {
                        "cell_type": "code",
                        "metadata": {},
                        "outputs": [],
                        "source": [f"notebook_url = {old_url}\n"],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
            path.write_text(
                json.dumps(notebook, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            self.assertTrue(
                migration.update_notebook_url(repo, migration.WELCOME_TEMPLATE_PATH)
            )
            updated = json.loads(path.read_text(encoding="utf-8"))
            source = "".join(updated["cells"][0]["source"])
            self.assertIn(
                "/contents/notebooks/{main_folder}/{subfolder}.ipynb", source
            )
            self.assertNotIn("/{subfolder}/{subfolder}.ipynb", source)
            self.assertFalse(
                migration.update_notebook_url(repo, migration.WELCOME_TEMPLATE_PATH)
            )
