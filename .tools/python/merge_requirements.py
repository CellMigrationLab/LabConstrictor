#!/usr/bin/env python3
"""Merge requirements files under a directory (e.g. notebooks/*) into a single root requirements file.

This updated script resolves simple version conflicts by choosing the newest version seen
for a given package (and emits a pinned `pkg==<newest>`). It still preserves
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


def read_requirements_file(path: Path, pkg_order: list, pkgs: dict, other_lines: OrderedDict):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return

    # Regex to capture name, optional extras, operator and version, and optional markers
    pkg_re = re.compile(r"^(?P<name>[A-Za-z0-9_.+-]+)(?P<extras>\[[^\]]+\])?\s*(?P<op>==|>=|<=|~=|!=|>|<)\s*(?P<ver>[^;\s]+)(?P<marker>\s*;.*)?$")

    for raw in text.splitlines():
        line = normalize_line(raw)
        if not line:
            continue

        parts = line.split(maxsplit=1)
        if parts[0] in ("-r", "--requirement") and len(parts) == 2:
            include = (path.parent / parts[1]).resolve()
            if include.exists():
                read_requirements_file(include, pkg_order, pkgs, other_lines)
            continue

        # Keep pip option lines (indexes, find-links, etc.) as-is
        if line.startswith("--") or line.startswith("-f ") or line.startswith("-i ") or line.startswith("-e "):
            other_lines.setdefault(line, None)
            continue

        # VCS or URL lines (git+, http(s)://, file:) keep as-is
        if any(line.startswith(prefix) for prefix in ("git+", "http://", "https://", "file:", "ssh://")):
            other_lines.setdefault(line, None)
            continue

        m = pkg_re.match(line)
        if not m:
            # plain package (unpinned) or marker-only spec
            key = line.split(";", 1)[0].strip().lower()
            if key not in pkgs:
                # record unpinned form
                pkgs[key] = {"name": line, "pinned": False, "ver": None}
                pkg_order.append(key)
            continue

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
                # prefer pinned if we see a pinned one
                pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}
            else:
                # both pinned: pick the newest version
                try:
                    if is_version_greater(ver, existing.get("ver")):
                        pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}
                except Exception:
                    # fallback: prefer lexicographically greater
                    if str(ver) > str(existing.get("ver")):
                        pkgs[base] = {"name": name + (extras or ""), "pinned": True, "ver": ver, "marker": marker}


def find_requirements_files(source_dir: Path):
    if not source_dir.exists():
        return []
    return sorted(source_dir.rglob("requirements*.txt"))


def read_environment_yaml(env_path: Path) -> dict:
    """Read environment.yaml and extract Python, JupyterLab, matplotlib versions."""
    if not env_path.exists():
        return {}
    try:
        data = yaml.safe_load(env_path.read_text(encoding="utf-8"))
        versions = {}
        for dep in data.get("dependencies", []):
            if isinstance(dep, str):
                if dep.startswith("python="):
                    versions["python"] = dep.split("=")[-1]
                elif dep.startswith("jupyterlab="):
                    versions["jupyterlab"] = dep.split("=")[-1]
                elif dep.startswith("matplotlib="):
                    versions["matplotlib"] = dep.split("=")[-1]
        return versions
    except Exception:
        return {}


def resolve_ipywidgets_version(env_versions: dict) -> str:
    """Resolve ipywidgets version based on Python, JupyterLab, matplotlib versions.
    
    Returns a version spec string like ">=7.0.0,<8.0.0" or a pinned version.
    """
    py_ver = env_versions.get("python", "3.11")
    jl_ver = env_versions.get("jupyterlab", "4.0")
    mpl_ver = env_versions.get("matplotlib", "3.0")
    
    # Simple heuristic: ipywidgets 8.x for modern stacks, 7.x for older
    try:
        py_major, py_minor = map(int, py_ver.split(".")[:2])
        jl_major = int(jl_ver.split(".")[0])
        
        if jl_major >= 4 and py_major >= 3 and py_minor >= 9:
            return "8.1.1"  # Latest stable for modern Python + JupyterLab 4
        elif py_major >= 3 and py_minor >= 8:
            return "8.0.4"  # Good for Python 3.8+
        else:
            return "7.7.2"  # Fallback for older environments
    except Exception:
        return ">=7.0.0"  # Safe fallback


def main():
    parser = argparse.ArgumentParser(description="Merge multiple requirements.txt files into one.")
    parser.add_argument("--source-dir", default="notebooks", help="Directory to scan for requirements files")
    parser.add_argument("--output", default="requirements.txt", help="Output requirements file to write")
    parser.add_argument("--sort", action="store_true", help="Sort final requirements alphabetically")
    parser.add_argument("--generate-env", action="store_true", help="Also generate a conda environment.yml with a pip: section")
    parser.add_argument("--env-output", default="environment.yml", help="Output environment.yml path")
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

    for f in files:
        if f.resolve() == output.resolve():
            continue
        read_requirements_file(f, pkg_order, pkgs, other_lines)

    # Build final list preserving first-seen package order
    final_lines = []

    # include other lines first (preserve order seen)
    for ol in other_lines.keys():
        final_lines.append(ol)

    # Check if ipywidgets is already present
    has_ipywidgets = "ipywidgets" in pkgs
    
    # If not, resolve and add it based on environment.yaml
    if not has_ipywidgets:
        env_path = Path(args.env_output) if args.generate_env else Path("environment.yaml")
        env_versions = read_environment_yaml(env_path)
        ipyw_version = resolve_ipywidgets_version(env_versions)
        
        # Add to pkgs and pkg_order
        pkgs["ipywidgets"] = {
            "name": "ipywidgets",
            "pinned": True,
            "ver": ipyw_version,
            "marker": ""
        }
        pkg_order.append("ipywidgets")
        print(f"Added ipywidgets=={ipyw_version} (resolved from environment)")

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

    for key in pkg_keys:
        info = pkgs.get(key)
        if not info:
            continue
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

    # Optionally write a conda environment.yml that starts with the requested header
    if args.generate_env:
        env_path = Path(args.env_output)
        # Required starting block per user request
        env_header = [
            "name: PROJECT_NAME",
            "channels:",
            "  - conda-forge",
            "  - defaults",
            "dependencies:",
            "  - python=3.11",
            "  - pip",
            "  - jupyterlab=4.0.12",
            "  - notebook=7.0.8",
        ]

        # For simplicity place all merged requirements under pip: (preserve order)
        pip_block = ["  - pip:"]
        for line in final_lines:
            # indent pip entries
            pip_block.append(f"    - {line}")

        env_content = "\n".join(env_header + pip_block) + "\n"
        env_path.write_text(env_content, encoding="utf-8")
        print(f"Wrote environment file to {env_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
