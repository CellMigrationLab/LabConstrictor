from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / ".template_sync"
    / "migrations"
    / "v0_1_12_to_v0_1_13.py"
)
BUMP_VERSION_PATH = REPO_ROOT / ".tools/python/bump_version.py"
RESOURCE_BUMP_VERSION_PATH = (
    REPO_ROOT
    / ".template_sync/resources/v0_1_12_to_v0_1_13/.tools/python/bump_version.py"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def welcome_notebook(owner: str = "ExampleOwner", repo: str = "ExampleProject") -> dict:
    code = f'''from ipywidgets import widgets, GridspecLayout


github_owner = "{owner}"
github_repo_name = "{repo}"

# Define notebooks with their metadata
notebooks = []

def load_table(version_response, project_version_response, notebooks):
    num_rows = 1
    grid = GridspecLayout(1 + num_rows, 7)
    display(widgets.HTML("""
    <style>
    .grid-header {{
        background-color: #ff6600 !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px !important;
        text-align: center !important;
    }}
    </style>
    """))

    update_src_button = widgets.Button(description="Update Source Code")
    def on_update_src_button_clicked(button):
        pass
    update_src_button.on_click(on_update_src_button_clicked)

    def button_update(main_folder, subfolder, row_idx):
        def show(button):
            grid[row_idx, 3] = widgets.HTML(f"<div style='text-align: center;'>{{online_latest_versions[main_folder][subfolder]}}</div>")
            grid[row_idx, 4] = widgets.HTML("<div style='text-align: center;'>✅ Up-to-date</div>")
            grid[row_idx, 5] = widgets.HTML("<div style='text-align: center;'>-</div>")
        return show

    online_latest_versions = {{"notebooks": {{"Example": "1.0.0"}}}}
    main_folder = "notebooks"
    subfolder = "Example"
    idx = 1
    nb = {{"description": "A longer notebook description used for layout testing."}}
    grid[idx, 2] = widgets.HTML(f"<div style='text-align: center;'>{{nb['description']}}</div>")
    update_button = widgets.Button(description="Update")
    update_button.on_click(button_update(main_folder, subfolder, row_idx=idx))

    grip_output = widgets.Output()
    display(grid, grip_output)
'''
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": code.splitlines(keepends=True),
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }



class VersionRepairTests(unittest.TestCase):
    def test_download_renderer_handles_placeholder_and_initialized_version(self):
        bump = load_module(BUMP_VERSION_PATH, "bump_version_for_test")

        pristine = (
            "https://github.com/o/r/releases/download/VERSION_NUMBER/"
            "Project-VERSION_NUMBER-Windows.exe"
        )
        initialized = (
            "https://github.com/o/r/releases/download/0.0.0/"
            "Project-0.0.0-Windows.exe"
        )

        self.assertIn(
            "/releases/download/0.0.4/Project-0.0.4-",
            bump.replace_version_placeholder(pristine, "0.0.4"),
        )
        self.assertIn(
            "/releases/download/0.0.4/Project-0.0.4-",
            bump.replace_version_placeholder(initialized, "0.0.4"),
        )

    def test_construct_repair_converges_even_when_conclusion_is_stale(self):
        bump = load_module(BUMP_VERSION_PATH, "bump_version_construct_test")
        original = (
            "name: Demo\n"
            "version: 0.0.3\n"
            "conclusion_text: Thank you! Installed Demo 0.0.0.\n"
        )
        updated = bump.bump_construct_text(original, "0.0.3", "0.0.3")
        self.assertIn("version: 0.0.3", updated)
        self.assertIn("Installed Demo 0.0.3.", updated)
        self.assertNotIn("0.0.0", updated)


class Migration013Tests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        (root / ".tools/python").mkdir(parents=True, exist_ok=True)
        (root / ".tools/python/bump_version.py").write_text(
            "# old bump-version implementation\n", encoding="utf-8"
        )

        (root / ".tools/templates").mkdir(parents=True, exist_ok=True)
        (root / ".tools/templates/download_executable_template.md").write_text(
            "https://github.com/CustomOwner/CustomRepo/releases/download/0.0.0/"
            "Custom_Project-0.0.0-Windows.exe\n"
            "bash Custom_Project-0.0.0-Linux.sh\n",
            encoding="utf-8",
        )

        (root / ".tools/docs").mkdir(parents=True, exist_ok=True)
        (root / ".tools/docs/download_executable.md").write_text(
            "https://github.com/CustomOwner/CustomRepo/releases/download/0.0.0/"
            "Custom_Project-0.0.0-Windows.exe\n"
            "bash Custom_Project-0.0.0-Linux.sh\n",
            encoding="utf-8",
        )

        (root / "construct.yaml").write_text(
            "name: Custom_Project\n"
            "version: 0.0.3\n"
            "conclusion_text: Thank you! Installed Custom_Project 0.0.0.\n",
            encoding="utf-8",
        )

        for relative in (
            Path(".tools/templates/Welcome_template.ipynb"),
            Path("app/menuinst/Welcome.ipynb"),
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(welcome_notebook(), ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )

    def test_migration_repairs_release_files_and_preserves_initialized_names(self):
        migration = load_module(MIGRATION_PATH, "migration_013")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_fixture(root)

            migration.migrate(root, {"from_version": "0.1.12", "to_version": "0.1.13"})

            self.assertEqual(
                (root / ".tools/python/bump_version.py").read_bytes(),
                RESOURCE_BUMP_VERSION_PATH.read_bytes(),
            )

            template = (root / ".tools/templates/download_executable_template.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("CustomOwner/CustomRepo", template)
            self.assertIn("Custom_Project", template)
            self.assertIn("VERSION_NUMBER", template)
            self.assertNotIn("0.0.0", template)

            download_doc = (root / ".tools/docs/download_executable.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("/releases/download/0.0.3/", download_doc)
            self.assertIn("Custom_Project-0.0.3-", download_doc)
            self.assertNotIn("0.0.0", download_doc)

            construct = (root / "construct.yaml").read_text(encoding="utf-8")
            self.assertIn("version: 0.0.3", construct)
            self.assertIn("Custom_Project 0.0.3", construct)
            self.assertNotIn("0.0.0", construct)

            for relative in (
                Path(".tools/templates/Welcome_template.ipynb"),
                Path("app/menuinst/Welcome.ipynb"),
            ):
                notebook = json.loads((root / relative).read_text(encoding="utf-8"))
                source = "".join(notebook["cells"][0]["source"])
                self.assertIn('github_owner = "ExampleOwner"', source)
                self.assertIn('github_repo_name = "ExampleProject"', source)
                self.assertIn("GRID_COLUMN_WIDTHS = (", source)
                self.assertIn("minmax(220px, 3.0fr)", source)
                self.assertIn('grid.layout.width = "100%"', source)
                self.assertIn('grid.layout.overflow = "auto"', source)
                self.assertIn("font-size: clamp(12px, 0.9vw, 15px)", source)
                self.assertIn("font-size: clamp(13px, 1vw, 16px)", source)
                self.assertIn("class='table-description'", source)
                self.assertIn("_widget_callback_output_cell_1 = widgets.Output()", source)
                self.assertGreaterEqual(
                    source.count("_widget_callback_output_cell_1.capture(clear_output=True, wait=True)"),
                    2,
                )
                self.assertEqual(source.count("display(_widget_callback_output_cell_1)"), 1)
                self.assertGreaterEqual(source.count("apply_grid_layout(grid)"), 3)

    def test_migration_is_idempotent(self):
        migration = load_module(MIGRATION_PATH, "migration_013_idempotent")
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

    def test_repository_bump_version_matches_migration_resource(self):
        self.assertEqual(BUMP_VERSION_PATH.read_bytes(), RESOURCE_BUMP_VERSION_PATH.read_bytes())

    def test_released_0_1_13_welcome_fixture_has_original_responsive_layout(self):
        fixture = REPO_ROOT / "tests/fixtures/welcome_0_1_13.ipynb"
        notebook = json.loads(fixture.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook.get("cells", [])
            if cell.get("cell_type") == "code"
        )
        self.assertIn("GRID_COLUMN_WIDTHS = (", source)
        self.assertIn("minmax(220px, 3.0fr)", source)
        self.assertIn('grid.layout.width = "100%"', source)
        self.assertIn('grid.layout.overflow = "auto"', source)
        self.assertIn("font-size: clamp(12px, 0.9vw, 15px)", source)
        self.assertIn("font-size: clamp(13px, 1vw, 16px)", source)
        self.assertIn("class='table-description'", source)
        self.assertIn("_widget_callback_output_cell_1 = widgets.Output()", source)
        self.assertGreaterEqual(
            source.count("_widget_callback_output_cell_1.capture(clear_output=True, wait=True)"),
            2,
        )
        self.assertEqual(source.count("display(_widget_callback_output_cell_1)"), 1)
        self.assertGreaterEqual(source.count("apply_grid_layout(grid)"), 3)
        compile(source, "welcome_0_1_13.ipynb", "exec")

if __name__ == "__main__":
    unittest.main()
