from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / ".template_sync"
    / "migrations"
    / "v0_1_13_to_v0_1_14.py"
)
WELCOME_TEMPLATE_PATH = REPO_ROOT / ".tools/templates/Welcome_template.ipynb"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_welcome_source(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        text = "".join(source) if isinstance(source, list) else str(source)
        if "grid = GridspecLayout(1 + num_rows, 7)" in text:
            return text
    raise AssertionError(f"Welcome table cell not found in {path}")


class Migration014Tests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        # Use the released 0.1.13 Welcome implementation as the migration input.
        source_root = REPO_ROOT
        historical = source_root / "tests/fixtures/welcome_0_1_13.ipynb"
        if not historical.exists():
            raise AssertionError(f"Missing fixture: {historical}")

        for relative in (
            Path(".tools/templates/Welcome_template.ipynb"),
            Path("app/menuinst/Welcome.ipynb"),
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(historical, target)

        # Simulate initialized downstream identity without altering table code.
        app_path = root / "app/menuinst/Welcome.ipynb"
        notebook = json.loads(app_path.read_text(encoding="utf-8"))
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            src = src.replace('github_owner = "GITHUB_OWNER"', 'github_owner = "ExampleOwner"')
            src = src.replace('github_repo_name = "GITHUB_REPO_NAME"', 'github_repo_name = "ExampleRepo"')
            cell["source"] = src.splitlines(keepends=True)
        app_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def assert_wrapping_layout(self, source: str) -> None:
        self.assertIn('"minmax(0, 1.4fr) "', source)
        self.assertIn('"minmax(0, 2.8fr) "', source)
        self.assertIn('grid.layout.min_width = "0"', source)
        self.assertIn('grid.layout.grid_auto_rows = "auto"', source)
        self.assertIn('grid.layout.overflow = "auto"', source)
        self.assertIn("def table_cell(", source)
        self.assertIn("def table_header(", source)
        self.assertIn("overflow-wrap: anywhere", source)
        self.assertIn("word-break: break-word", source)
        self.assertIn("grid[idx, 0] = table_cell(nb[\"name\"])", source)
        self.assertIn("grid[idx, 1] = table_cell(main_folder)", source)
        self.assertIn('grid[idx, 2] = table_cell(nb["description"], align="left")', source)
        self.assertIn('grid[0, 6] = table_header("Open Notebook")', source)
        self.assertIn('min_width="140px"', source)
        self.assertNotIn("class='table-description'", source)
        self.assertNotIn("⬇️ Click to Open the Notebook ⬇️", source)
        self.assertGreaterEqual(source.count("apply_grid_layout(grid)"), 3)
        compile(source, "Welcome.ipynb", "exec")

    def test_migration_updates_both_welcome_notebooks_and_preserves_identity(self):
        migration = load_module(MIGRATION_PATH, "migration_014")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_fixture(root)

            migration.migrate(root, {"from_version": "0.1.13", "to_version": "0.1.14"})

            template_source = find_welcome_source(root / ".tools/templates/Welcome_template.ipynb")
            app_source = find_welcome_source(root / "app/menuinst/Welcome.ipynb")
            self.assert_wrapping_layout(template_source)
            self.assert_wrapping_layout(app_source)

            self.assertIn('github_owner = "GITHUB_OWNER"', template_source)
            self.assertIn('github_repo_name = "GITHUB_REPO_NAME"', template_source)
            self.assertIn('github_owner = "ExampleOwner"', app_source)
            self.assertIn('github_repo_name = "ExampleRepo"', app_source)

    def test_migration_is_idempotent(self):
        migration = load_module(MIGRATION_PATH, "migration_014_idempotent")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_fixture(root)
            migration.migrate(root, {})
            first = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            migration.migrate(root, {})
            second = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first, second)

    def test_repository_template_is_0_1_14_wrapping_layout(self):
        source = find_welcome_source(WELCOME_TEMPLATE_PATH)
        self.assert_wrapping_layout(source)
        self.assertIn('github_owner = "GITHUB_OWNER"', source)
        self.assertIn('github_repo_name = "GITHUB_REPO_NAME"', source)
        self.assertIn("notebooks = DICT_OF_NOTEBOOKS", source)


if __name__ == "__main__":
    unittest.main()
