#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys
import textwrap
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONSTRUCT = ROOT / "construct.yaml"

VERSION_RE = re.compile(r'^version:\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', re.MULTILINE)

def read_current_version() -> tuple[str, str]:
    # Read construct.yaml to find the current version
    with CONSTRUCT.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if "version" in data:
        return data, data["version"]
    else:
        sys.exit("Could not find version in construct.yaml")

def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")


def bump_construct(data, old_version, new_version):
    data['version'] = new_version
    if "conclusion_text" in data:
        data["conclusion_text"] = re.sub(
            rf'(Thank you for installing PROJECT_NAME v){re.escape(old_version)}(!)',
            rf'\g<1>{new_version}\g<2>',  # Use named groups to avoid ambiguity
            data["conclusion_text"],
            count=1,
        )
    return data

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update project version across release artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Example:
              python .tools/python/bump_version.py 0.0.4
            """
        ),
    )
    parser.add_argument("new_version", help="SemVer version, e.g. 0.0.4")
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", args.new_version):
        sys.exit("Version must look like X.Y.Z")

    construct_text, current = read_current_version()
    if args.new_version == current:
        print(f"Version already at {current}; nothing to update.")
        return

    updated_construct = bump_construct(construct_text, current, args.new_version)

    # Write construct.yaml
    with CONSTRUCT.open("w", encoding="utf-8") as f:
        yaml.dump(updated_construct, f, sort_keys=False)
    print(f"Bumped {current} -> {args.new_version}")


if __name__ == "__main__":
    main()
