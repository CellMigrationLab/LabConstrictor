import sys
from pathlib import Path
import yaml
import re


def load_construct(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def save_construct_surgical(path: Path, data: dict, original_text: str) -> str:
    """Update only extra_files section while preserving the rest of the file structure."""
    # Convert updated extra_files back to YAML string
    extra_files = data.get("extra_files", [])
    extra_files_yaml = "extra_files:\n"
    for item in extra_files:
        if isinstance(item, dict):
            for src, dst in item.items():
                extra_files_yaml += f"- {src}: {dst}\n"
        else:
            extra_files_yaml += f"- {item}\n"
    
    # Find and replace the extra_files section in the original text
    pattern = r"extra_files:\n((?:- .+\n)*)"
    if re.search(pattern, original_text):
        updated = re.sub(pattern, extra_files_yaml, original_text)
        path.write_text(updated, encoding="utf-8")
    else:
        # Fallback: if no extra_files found, use standard dump
        path.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def extract_project_folder(extra_files: list) -> str:
    """Extract the project folder name from existing mappings (e.g., from Welcome.ipynb dest)."""
    for item in extra_files:
        if isinstance(item, dict):
            for src, dst in item.items():
                if "Welcome.ipynb" in src or "Welcome.ipynb" in dst:
                    # Extract first folder from destination path
                    parts = dst.split("/")
                    if parts:
                        return parts[0]
    # Fallback
    return "PROJECT_NAME"


def ensure_notebooks_in_extra_files(construct_data: dict, notebooks_root: Path) -> int:
    extra_files = construct_data.get("extra_files")
    if extra_files is None:
        extra_files = []
        construct_data["extra_files"] = extra_files

    # Extract the project folder name from existing mappings
    project_folder = extract_project_folder(extra_files)

    # Normalize existing entries into a dict for quick lookup
    existing_sources = set()
    existing_dests = set()
    normalized_items = []

    for item in extra_files:
        # Items can be either dicts (k: v) or strings with mapping? Assume dicts per example
        if isinstance(item, dict):
            for src, dst in item.items():
                existing_sources.add(str(src))
                existing_dests.add(str(dst))
                normalized_items.append({str(src): str(dst)})
        else:
            # If strings are present, keep them
            normalized_items.append(item)

    ntbk_added = 0
    repo_root = Path(".").resolve()

    # Include all notebooks under notebooks/ directory
    for ipynb in notebooks_root.rglob("*.ipynb"):
        rel = ipynb.relative_to(repo_root).as_posix()
        if not rel.startswith("notebooks/"):
            continue
        src = rel
        dst = f"{project_folder}/{rel}"

        if src in existing_sources or dst in existing_dests:
            continue

        normalized_items.append({src: dst})
        ntbk_added += 1

    # First get the name of the package from setup.py
    setup_path = repo_root / "setup.py"
    project_name = "PROJECT_NAME"
    if setup_path.exists():
        setup_text = setup_path.read_text(encoding="utf-8")
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', setup_text)
        if name_match:
            project_name = name_match.group(1)

    # Include all the Python scripts under src/ directory
    src_added = 0
    src_root = Path("src").resolve()
    included_src_flag = False
    for py_file in src_root.rglob("*.py"):
        rel = py_file.relative_to(repo_root).as_posix()
        if not rel.startswith("src/"):
            continue
        src = rel
        dst = f"{project_folder}/src/{project_name}/{rel.replace('src/', '')}"

        if src in existing_sources or dst in existing_dests:
            continue

        normalized_items.append({src: dst})
        included_src_flag = True
        src_added += 1

    if included_src_flag:
        # Also include the setup.py file at the root if not already included
        setup_src = "setup.py"
        setup_dst = f"{project_folder}/setup.py"
        if setup_src not in existing_sources and setup_dst not in existing_dests:
            normalized_items.append({setup_src: setup_dst})
            src_added += 1

    # Optionally sort entries (dicts by their single key) for determinism
    def sort_key(item):
        if isinstance(item, dict):
            # single-key dict
            k = next(iter(item.keys()))
            return (0, k)
        return (1, str(item))

    normalized_items.sort(key=sort_key)
    construct_data["extra_files"] = normalized_items

    return ntbk_added, src_added


def main():
    construct_path = Path("construct.yaml") if len(sys.argv) < 2 else Path(sys.argv[1])
    notebooks_root = Path("notebooks").resolve()

    if not construct_path.exists():
        print(f"construct.yaml not found at: {construct_path}", file=sys.stderr)
        sys.exit(1)

    # Read original text to preserve formatting
    original_text = construct_path.read_text(encoding="utf-8")
    
    data = load_construct(construct_path)
    ntbk_added, src_added = ensure_notebooks_in_extra_files(data, notebooks_root)
    
    # Write using surgical update to preserve platform-specific scripts
    save_construct_surgical(construct_path, data, original_text)
    print(f"Added {ntbk_added} notebook(s) and {src_added} source file(s) to extra_files.")

if __name__ == "__main__":
    main()
