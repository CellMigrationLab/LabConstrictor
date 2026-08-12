from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any


RESOURCE_ROOT = (
    Path(__file__).resolve().parents[1] / "resources" / "v0_1_12_to_v0_1_13"
)
BUMP_VERSION_PATH = Path(".tools/python/bump_version.py")
DOWNLOAD_TEMPLATE_PATH = Path(".tools/templates/download_executable_template.md")
DOWNLOAD_DOC_PATHS = (
    Path(".tools/docs/download_executable.md"),
    Path("docs/download_executable.md"),
)
CONSTRUCT_PATH = Path("construct.yaml")
WELCOME_PATHS = (
    Path(".tools/templates/Welcome_template.ipynb"),
    Path("app/menuinst/Welcome.ipynb"),
)

VERSION_LINE_RE = re.compile(
    r'^(version:\s*)(?P<quote>["\']?)(?P<version>\d+\.\d+\.\d+)(?P=quote)(?P<trailing>\s*(?:#.*)?)$',
    re.MULTILINE,
)
CONCLUSION_LINE_RE = re.compile(
    r'^(conclusion_text:\s*)(?:(?P<quote>["\'])(?P<quoted_body>.*?)(?P=quote)|(?P<bare_body>.*?))(?P<trailing>\s*(?:#.*)?)$',
    re.MULTILINE,
)
RELEASE_VERSION_RE = re.compile(r"/releases/download/(\d+\.\d+\.\d+)/")
SEMVER_RE = re.compile(r"\b\d+\.\d+\.\d+\b")

GRID_CONFIG = '''GRID_COLUMN_WIDTHS = (\n    "1.2fr "\n    "1.0fr "\n    "3.0fr "\n    "0.8fr "\n    "1.4fr "\n    "0.8fr "\n    "1.8fr"\n)\n\n\ndef apply_grid_column_widths(grid):\n    """Apply responsive widths tuned to the expected content of each column."""\n    grid.layout.grid_template_columns = GRID_COLUMN_WIDTHS\n\n\n'''

CALLBACK_BLOCK = '''                                        grid[row_idx, 3] = widgets.HTML(f"<div style='text-align: center;'>{online_latest_versions[main_folder][subfolder]}</div>")\n                                        grid[row_idx, 4] = widgets.HTML("<div style='text-align: center;'>✅ Up-to-date</div>")\n                                        grid[row_idx, 5] = widgets.HTML("<div style='text-align: center;'>-</div>")\n'''


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def normalize_newlines(text: str, newline: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", newline)


def copy_bump_version(repo_root: Path) -> bool:
    source = RESOURCE_ROOT / BUMP_VERSION_PATH
    destination = repo_root / BUMP_VERSION_PATH
    if not source.is_file():
        raise ValueError(f"Missing migration resource: {source}")

    source_text = read_text(source)
    if destination.exists():
        existing_text = read_text(destination)
        newline = detect_newline(existing_text)
    else:
        existing_text = ""
        newline = detect_newline(source_text)

    rendered = normalize_newlines(source_text, newline)
    if rendered == existing_text:
        return False

    write_text(destination, rendered)
    print(f"Updated {BUMP_VERSION_PATH}")
    return True


def normalize_download_template(repo_root: Path) -> bool:
    path = repo_root / DOWNLOAD_TEMPLATE_PATH
    if not path.is_file():
        print(f"Skipping missing file: {DOWNLOAD_TEMPLATE_PATH}")
        return False

    original = read_text(path)
    if "VERSION_NUMBER" in original:
        return False

    versions = set(RELEASE_VERSION_RE.findall(original))
    if not versions:
        print(
            f"Skipping {DOWNLOAD_TEMPLATE_PATH}: no release version placeholder "
            "or explicit release version was found"
        )
        return False

    updated = original
    for version in versions:
        updated = updated.replace(version, "VERSION_NUMBER")

    if updated == original:
        return False

    write_text(path, updated)
    print(f"Normalized release version placeholder in {DOWNLOAD_TEMPLATE_PATH}")
    return True


def read_project_version(repo_root: Path) -> str | None:
    path = repo_root / CONSTRUCT_PATH
    if not path.is_file():
        return None
    match = VERSION_LINE_RE.search(read_text(path))
    return match.group("version") if match else None


def align_construct_conclusion(repo_root: Path, project_version: str | None) -> bool:
    if not project_version:
        return False

    path = repo_root / CONSTRUCT_PATH
    if not path.is_file():
        return False

    original = read_text(path)

    def repl(match: re.Match) -> str:
        quote = match.group("quote") or ""
        body = match.group("quoted_body") if quote else (match.group("bare_body") or "")
        if "VERSION_NUMBER" in body:
            updated_body = body.replace("VERSION_NUMBER", project_version)
        else:
            updated_body = SEMVER_RE.sub(project_version, body, count=1)
        return (
            f"{match.group(1)}{quote}{updated_body}{quote}"
            f"{match.group('trailing')}"
        )

    updated = CONCLUSION_LINE_RE.sub(repl, original, count=1)
    if updated == original:
        return False

    write_text(path, updated)
    print(f"Aligned {CONSTRUCT_PATH} conclusion text to {project_version}")
    return True


def align_download_docs(repo_root: Path, project_version: str | None) -> bool:
    if not project_version:
        return False

    changed = False
    for relative_path in DOWNLOAD_DOC_PATHS:
        path = repo_root / relative_path
        if not path.is_file():
            continue

        original = read_text(path)
        versions = set(RELEASE_VERSION_RE.findall(original))
        updated = original
        for version in versions:
            updated = updated.replace(version, project_version)

        if updated != original:
            write_text(path, updated)
            print(f"Aligned {relative_path} download links to {project_version}")
            changed = True

    return changed


def update_welcome_notebook(repo_root: Path, relative_path: Path) -> bool:
    path = repo_root / relative_path
    if not path.is_file():
        print(f"Skipping missing file: {relative_path}")
        return False

    original_text = read_text(path)
    newline = detect_newline(original_text)
    try:
        notebook = json.loads(original_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to parse {relative_path} as JSON") from exc

    changed = False
    found_grid = False
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        source_is_list = isinstance(source, list)
        src = "".join(source) if source_is_list else str(source)
        if "grid = GridspecLayout(1 + num_rows, 7)" not in src:
            continue

        found_grid = True
        normalized = src.replace("\r\n", "\n")

        if "GRID_COLUMN_WIDTHS = (" not in normalized:
            marker = "def load_table(version_response, project_version_response, notebooks):\n"
            if marker not in normalized:
                raise ValueError(
                    f"Unable to find load_table insertion point in {relative_path}"
                )
            normalized = normalized.replace(marker, GRID_CONFIG + marker, 1)
            changed = True

        lines = normalized.splitlines(keepends=True)

        callback_apply_present = False
        for index, line in enumerate(lines):
            if line.strip() != "apply_grid_column_widths(grid)":
                continue
            previous = lines[index - 1].strip() if index > 0 else ""
            if previous.startswith("grid[row_idx, 5] = widgets.HTML"):
                callback_apply_present = True
                break

        if not callback_apply_present:
            insert_index = None
            indent = ""
            for index, line in enumerate(lines):
                if line.strip().startswith("grid[row_idx, 5] = widgets.HTML"):
                    insert_index = index + 1
                    indent = line[: len(line) - len(line.lstrip())]
                    break
            if insert_index is None:
                raise ValueError(
                    f"Unable to find notebook-update grid block in {relative_path}"
                )
            lines.insert(insert_index, f"{indent}apply_grid_column_widths(grid)\n")
            changed = True

        display_index = None
        for index, line in enumerate(lines):
            if line.strip() == "display(grid, grip_output)":
                display_index = index
                break
        if display_index is None:
            raise ValueError(f"Unable to find grid display in {relative_path}")

        previous = lines[display_index - 1].strip() if display_index > 0 else ""
        if previous != "apply_grid_column_widths(grid)":
            display_line = lines[display_index]
            indent = display_line[: len(display_line) - len(display_line.lstrip())]
            lines.insert(display_index, f"{indent}apply_grid_column_widths(grid)\n")
            changed = True

        normalized = "".join(lines)

        if changed:
            rendered_source = normalize_newlines(normalized, "\n")
            cell["source"] = (
                rendered_source.splitlines(keepends=True)
                if source_is_list
                else rendered_source
            )
        break

    if not found_grid:
        print(f"Skipping {relative_path}: expected Welcome table grid was not found")
        return False
    if not changed:
        return False

    rendered = json.dumps(notebook, ensure_ascii=False, indent=1)
    if original_text.endswith(("\n", "\r\n")):
        rendered += newline
    write_text(path, rendered)
    print(f"Updated responsive column widths in {relative_path}")
    return True


def migrate(repo_root: Path, context: dict[str, Any]) -> None:
    _ = context

    changed_any = False
    changed_any = copy_bump_version(repo_root) or changed_any
    changed_any = normalize_download_template(repo_root) or changed_any

    project_version = read_project_version(repo_root)
    changed_any = align_construct_conclusion(repo_root, project_version) or changed_any
    changed_any = align_download_docs(repo_root, project_version) or changed_any

    for relative_path in WELCOME_PATHS:
        changed_any = update_welcome_notebook(repo_root, relative_path) or changed_any

    if not changed_any:
        print("No repository changes were required for this migration.")
