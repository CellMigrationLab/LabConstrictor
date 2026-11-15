"""The notebook changelog quotes only the subject line of the commit, never its body or trailers (Co-authored-by and the like)."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("update_changelog_test", ROOT / ".tools/python/update_changelog.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CommitMessageTests(unittest.TestCase):
    def test_changelog_entry_has_the_subject_line_only(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = {**os.environ, "GIT_AUTHOR_NAME": "A", "GIT_AUTHOR_EMAIL": "a@example.org",
                   "GIT_COMMITTER_NAME": "A", "GIT_COMMITTER_EMAIL": "a@example.org"}
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
            notebook_dir = repo / "notebooks" / "Demo"
            notebook_dir.mkdir(parents=True)
            (notebook_dir / "Demo.ipynb").write_text("{}", encoding="utf-8")
            versions = repo / "notebooks" / "notebook_latest_versions.yaml"
            versions.write_text("Demo: 0.0.2\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
            message = "Bump Demo to 0.0.2\n\nLonger body text.\n\nCo-authored-by: Someone <s@example.org>\nSigned-off-by: A <a@example.org>\n"
            subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True, env=env)
            cwd = os.getcwd()
            os.chdir(repo)
            try:
                info = module.get_git_commit_info()
                self.assertEqual(info["message"], "Bump Demo to 0.0.2")
                module.create_or_update_changelog("Demo", "0.0.1", "0.0.2", info, str(versions))
            finally:
                os.chdir(cwd)
            changelog = (notebook_dir / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("- Message: Bump Demo to 0.0.2", changelog)
        for leaked in ("Co-authored-by", "Signed-off-by", "Longer body text"):
            self.assertNotIn(leaked, changelog)


if __name__ == "__main__":
    unittest.main()
