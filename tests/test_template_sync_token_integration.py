from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / ".template_sync"
    / "migrations"
    / "v0_1_11_to_v0_1_12.py"
)


def load_migration_module():
    spec = importlib.util.spec_from_file_location("token_setup_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TokenIntegrationMigrationTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        files = {
            "README.md": "# Custom scientific project\n\nKeep this project-specific text.\n",
            ".tools/docs/README.md": (
                "# Documentation\n\n## GitHub management\n\n"
                "- [Troubleshooting](troubleshooting.md)\n"
            ),
            ".tools/docs/before_getting_started.md": (
                "# Before getting started\n\nExisting guidance.\n\n---\n\n"
                "<div align=\"center\">Home</div>\n"
            ),
            ".tools/docs/create_repository.md": (
                "# Create repository\n\nExisting creation steps.\n\n---\n\n"
                "<div align=\"center\">Home</div>\n"
            ),
            ".tools/docs/initialise_repository.md": (
                "# Initialise repository\n\nExisting initialisation text.\n"
            ),
            ".tools/docs/personal_access_token.md": (
                "# Notebook token\n\nExisting notebook-token guidance.\n"
            ),
            ".tools/docs/troubleshooting.md": (
                "# Troubleshooting\n\n"
                "## Synchronisation is failing on GitHub Actions\n\n"
                "Old GITHUB_TOKEN advice.\n\n"
                "## Other issue\n\nKeep this section.\n"
            ),
            ".tools/docs/workflow_status.md": (
                "# Workflow status\n\nExisting workflow guidance.\n"
            ),
            ".tools/docs/accept_pull_request.md": (
                "# Accept a pull request\n\nExisting PR guidance.\n"
            ),
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_migration_installs_workflow_guide_and_links_without_losing_custom_text(self):
        module = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_fixture(root)

            module.migrate(root, {"from_version": "0.1.11", "to_version": "0.1.12"})

            workflow = (root / ".github/workflows/sync_template.yml").read_text(
                encoding="utf-8"
            )
            guide = (root / ".tools/docs/template_synchronization.md").read_text(
                encoding="utf-8"
            )
            readme = (root / "README.md").read_text(encoding="utf-8")
            troubleshooting = (root / ".tools/docs/troubleshooting.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("token: ${{ secrets.LABCONSTRICTOR_SYNC_TOKEN }}", workflow)
            self.assertIn("persist-credentials: false", workflow)
            self.assertIn("Check synchronization token setup", workflow)
            self.assertNotIn("echo '`${{ secrets.LABCONSTRICTOR_SYNC_TOKEN }}`", workflow)
            self.assertIn("Create the synchronization token", guide)
            self.assertIn("workflows=write", guide)
            self.assertIn("Keep this project-specific text.", readme)
            self.assertIn(".tools/docs/template_synchronization.md", readme)
            self.assertIn("Keep this section.", troubleshooting)
            self.assertIn("LABCONSTRICTOR_SYNC_TOKEN", troubleshooting)

            for relative in (
                ".tools/docs/README.md",
                ".tools/docs/before_getting_started.md",
                ".tools/docs/create_repository.md",
                ".tools/docs/initialise_repository.md",
                ".tools/docs/personal_access_token.md",
                ".tools/docs/troubleshooting.md",
                ".tools/docs/workflow_status.md",
                ".tools/docs/accept_pull_request.md",
            ):
                self.assertIn(
                    "template_synchronization.md",
                    (root / relative).read_text(encoding="utf-8"),
                    relative,
                )

    def test_migration_is_idempotent(self):
        module = load_migration_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_fixture(root)
            module.migrate(root, {})

            first = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            module.migrate(root, {})
            second = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first, second)

    def test_repository_template_files_match_migration_resources(self):
        resource_root = (
            REPO_ROOT
            / ".template_sync"
            / "resources"
            / "v0_1_11_to_v0_1_12"
        )
        for relative in (
            Path(".github/workflows/sync_template.yml"),
            Path(".tools/docs/template_synchronization.md"),
        ):
            self.assertEqual(
                (REPO_ROOT / relative).read_bytes(),
                (resource_root / relative).read_bytes(),
                relative,
            )


if __name__ == "__main__":
    unittest.main()
