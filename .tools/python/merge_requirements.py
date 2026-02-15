#!/usr/bin/env python3
"""Merge requirements files under a directory (e.g. notebooks/*) into a single
root requirements file.

The script now supports both classic requirements.txt files and the new
requirements.yaml format used by notebooks. For YAML files, it merges the
`python_version` (picking the newest) and the `dependencies` list while
discarding per-notebook descriptions.

It resolves simple version conflicts by choosing the newest version seen for a
given package (and emits a pinned `pkg==<newest>`). It still preserves
non-package lines (pip options, VCS/URLs) and supports simple `-r` includes.

It also automatically adds ipywidgets if missing, with a version determined by
Python, JupyterLab, and matplotlib versions from environment.yaml.
"""
from pathlib import Path
import argparse
import sys
from collections import OrderedDict
from datetime import datetime
import re
import yaml


# Regex to capture name, optional extras, operator and version, and optional markers
pkg_re = re.compile(r"^(?P<name>[A-Za-z0-9_.+-]+)(?P<extras>\[[^\]]+\])?\s*(?P<op>==|>=|<=|~=|!=|>|<)\s*(?P<ver>[^;\s]+)(?P<marker>\s*;.*)?$")


def normalize_line(line: str) -> str:
    # Remove inline comments and surrounding whitespace.
    if "#" in line:
        line = line.split("#", 1)[0]
    return line.strip()


try:
    # Prefer packaging.version for robust version comparison
    from packaging.version import Version, InvalidVersion

    def parse_version(v: str):
        try:
            return Version(v)
        except InvalidVersion:
            return v

    def is_version_greater(a, b):
        try:
            return Version(a) > Version(b)
        except Exception:
            return str(a) > str(b)

except Exception:
    # Fallback: simple numeric-aware comparator
    def _split_parts(v: str):
        parts = re.split(r"[.\-+_]|(?=[a-zA-Z])", v)
        key = []
        for p in parts:
            if not p:
                continue
            if p.isdigit():
                key.append((0, int(p)))
            else:
                key.append((1, p))
        return tuple(key)

    def parse_version(v: str):
        return _split_parts(v)

    def is_version_greater(a, b):
        return parse_version(a) > parse_version(b)


def merge_python_version(filepath: str | None, current: str | None, candidate: str | None):
    """Pick the newest python_version string, if provided."""
    if not candidate:
        return current
    if current is None:
        return candidate
    if current == candidate:
        return current
    else:
        raise ValueError(f"Conflicting python_version found {current} vs {candidate} when processing {filepath}")


def process_requirement_line(line: str, pkg_order: list, pkgs: dict, other_lines: OrderedDict, base_dir: Path | None = None):
    """Handle a single requirement line (shared between txt and yaml inputs)."""
    if not line:
        return

    parts = line.split(maxsplit=1)
    if parts[0] in ("-r", "--requirement") and len(parts) == 2:
        include_path = Path(parts[1]) if base_dir is None else (base_dir / parts[1])
        include = include_path.resolve()
        if include.exists():
            read_requirements_file(include, pkg_order, pkgs, other_lines)
        return

    # Keep pip option lines (indexes, find-links, etc.) as-is
    if line.startswith("--") or line.startswith("-f ") or line.startswith("-i ") or line.startswith("-e "):
        other_lines.setdefault(line, None)
        return

    # VCS or URL lines (git+, http(s)://, file:) keep as-is
    if any(line.startswith(prefix) for prefix in ("git+", "http://", "https://", "file:", "ssh://")):
        other_lines.setdefault(line, None)
        return

    m = pkg_re.match(line)
    if not m:
        # plain package (unpinned) or marker-only spec
        key = line.split(";", 1)[0].strip().lower()
        if key not in pkgs:
            pkgs[key] = {"name": line, "pinned": False, "ver": None}
            pkg_order.append(key)
        return

    name = m.group("name")
    extras = m.group("extras") or ""
    ver = m.group("ver")
    marker = m.group("marker") or ""

    base = name.lower()
    if base not in pkgs:
        pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}
        pkg_order.append(base)
    else:
        existing = pkgs[base]
        if not existing.get("pinned"):
            pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}
        else:
            try:
                if is_version_greater(ver, existing.get("ver")):
                    pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}
            except Exception:
                if str(ver) > str(existing.get("ver")):
                    pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}


def read_requirements_file(path: Path, pkg_order: list, pkgs: dict, other_lines: OrderedDict):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return

    for raw in text.splitlines():
        line = normalize_line(raw)
        process_requirement_line(line, pkg_order, pkgs, other_lines, base_dir=path.parent)


def read_requirements_yaml(path: Path, pkg_order: list, pkgs: dict, other_lines: OrderedDict) -> str | None:
    """Read requirements.yaml and return its python_version if present."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    python_version = data.get("python_version")
    dependencies = data.get("dependencies", []) or []

    for dep in dependencies:
        line = normalize_line(str(dep))
        process_requirement_line(line, pkg_order, pkgs, other_lines, base_dir=path.parent)

    return python_version


def find_requirements_files(source_dir):
    if not source_dir.exists():
        return []

    patterns = ["requirements.yaml", "requirements.yml", "requirements*.txt"]

    files = []
    for pattern in patterns:
        files.extend(source_dir.rglob(pattern))
    return sorted({f.resolve() for f in files})


def resolve_ipywidgets_version(py_version, jl_version):
    """Resolve ipywidgets version based on Python, JupyterLab versions.
    
    Returns a version spec string like ">=7.0.0,<8.0.0" or a pinned version.
    """
    
    # Simple heuristic: ipywidgets 8.x for modern stacks, 7.x for older
    try:
        py_major, py_minor = map(int, py_version.split(".")[:2])
        jl_major = int(jl_version.split(".")[0])
        
        if jl_major >= 4 and py_major >= 3 and py_minor >= 9:
            return "8.1.7"  # Latest stable for modern Python + JupyterLab 4
        elif py_major >= 3 and py_minor >= 7:
            return "8.1.6"  # Good for Python 3.7+
        else:
            return "7.7.2"  # Fallback for older environments
    except Exception:
        return ">=7.0.0"  # Safe fallback


def main():
    parser = argparse.ArgumentParser(description="Merge multiple requirements files (txt or yaml) into one.")
    parser.add_argument("--source-dir", default="notebooks", help="Directory to scan for requirements files")
    parser.add_argument("--output", default="requirements.txt", help="Output requirements file to write")
    parser.add_argument("--sort", action="store_true", help="Sort final requirements alphabetically")
    args = parser.parse_args()

    source = Path(args.source_dir)
    output = Path(args.output)

    files = find_requirements_files(source)
    if not files:
        print(f"No requirements files found under {source}, writing empty {output}")
        output.write_text("# Generated requirements (none found)\n", encoding="utf-8")
        return 0

    pkg_order = []
    pkgs = {}  # base -> {name, pinned, ver, marker}
    other_lines = OrderedDict()
    python_version = None

    for f in files:
        if f.resolve() == output.resolve():
            continue
        if f.suffix.lower() in {".yaml", ".yml"}:
            candidate_py = read_requirements_yaml(f, pkg_order, pkgs, other_lines)
            python_version = merge_python_version(f, python_version, candidate_py)
        else:
            read_requirements_file(f, pkg_order, pkgs, other_lines)

    # Build final list preserving first-seen package order
    final_lines = []

    # include other lines first (preserve order seen)
    for ol in other_lines.keys():
        final_lines.append(ol)

    # Ensure jl-hidecode is present with a pinned version
    if "jl-hidecode" not in pkgs:
        pkgs["jl-hidecode"] = {
            "name": "jl-hidecode",
            "pinned": True,
            "ver": "0.0.1",
            "marker": ""
        }
        pkg_order.append("jl-hidecode")
        print("Added jl-hidecode==0.0.1 (enforced)")

    # collect package lines
    if args.sort:
        pkg_keys = sorted(pkg_order, key=str.casefold)
    else:
        pkg_keys = pkg_order

    # Check if ipywidgets is present; if not, add it with resolved version
    if "jupyterlab" not in pkgs:
        jl_ver = "4.4.0"

    # Check if ipywidgets is present; if not, add it to the packages
    if "ipywidgets" not in pkgs:
        iw_version = resolve_ipywidgets_version(python_version, jl_ver)
        pkgs["ipywidgets"] = {
            "name": "ipywidgets",
            "pinned": True,
            "ver": iw_version,
            "marker": ""
        }
        pkg_order.append("ipywidgets")
        print(f"Added ipywidgets=={iw_version} (resolved)")

    for key in pkg_keys:
        info = pkgs.get(key)
        if not info:
            continue

        # Check if jupyterlab is present:
        if key == "jupyterlab":
            jl_info = pkgs.get(key)
            if jl_info and jl_info.get("pinned") and jl_info.get("ver"):
                jl_ver = jl_info["ver"]
            else:
                jl_ver = "4.4.0"

        if info.get("pinned") and info.get("ver"):
            final_lines.append(f"{info['name']}=={info['ver']}{info.get('marker','')}")
        else:
            final_lines.append(info["name"])

    header = (
        f"# Generated by .tools/python/merge_requirements.py on {datetime.utcnow().isoformat()}Z\n"
        f"# Source files: {', '.join(str(p) for p in files)}\n"
        "# ---\n"
    )
    content = header + "\n".join(final_lines) + ("\n" if final_lines and not final_lines[-1].endswith("\n") else "")
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output} with {len(final_lines)} entries (from {len(files)} files)")

    # Create the environment.yaml if not present
    env_path = Path("environment.yaml")
    if not env_path.exists():
        print(f"{env_path} not found, please be sure to create one.")
        raise FileNotFoundError(f"{env_path} not found.")
    else:
        data = yaml.safe_load(env_path.read_text(encoding="utf-8"))
        dependencies = data.get("dependencies", [])
        for i, dep in enumerate(dependencies):
            if isinstance(dep, str):
                if dep.startswith("python="):
                    dependencies[i] = f"python={python_version}"
                elif dep.startswith("jupyterlab="):
                    dependencies[i] = f"jupyterlab={jl_ver}"
        data["dependencies"] = dependencies
        env_path.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
        print(f"Updated {env_path} with python={python_version} and jupyterlab={jl_ver}")

    # Replace on setup.py the Python version
    setup_path = Path("setup.py")
    if setup_path.exists():
        setup_text = setup_path.read_text(encoding="utf-8")
        pattern = r'python_requires\s*=\s*["\'][><=\.0-9 ]+(PYTHON\_VERSION)?["\']'
        new_setup_text = re.sub(pattern, f'python_requires=">={python_version}"', setup_text)
        setup_path.write_text(new_setup_text, encoding="utf-8")
        print(f"Updated {setup_path} with python_requires>={python_version}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
