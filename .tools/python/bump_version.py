#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONSTRUCT = ROOT / "construct.yaml"
DOC = ROOT / "docs" / "getting_started" / "Local_Installation.md"

VERSION_RE = re.compile(r'^version:\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', re.MULTILINE)

def read_current_version() -> tuple[str, str]:
    text = CONSTRUCT.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        sys.exit("Could not find version in construct.yaml")
    return text, match.group("version")


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")


def bump_construct(text: str, old: str, new: str) -> str:
    text = VERSION_RE.sub(f'version: "{new}"', text, count=1)
    text = re.sub(
        rf'(Thank you for installing PROJECT_NAME v){re.escape(old)}(!)',
        rf'\g<1>{new}\g<2>',  # Use named groups to avoid ambiguity
        text,
        count=1,
    )
    return text


def bump_doc(text: str, old: str, new: str) -> str:
    text = text.replace(
        f"releases/download/{old}/",
        f"releases/download/{new}/",
    )
    text = re.sub(
        rf'PROJECT_NAME-{re.escape(old)}-(Windows|Linux|macOS)(?P<suffix>[-\w.]*)',
        lambda m: f"PROJECT_NAME-{new}-{m.group(1)}{m.group('suffix')}",
        text,
    )
    return text


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
    doc_text = DOC.read_text(encoding="utf-8")
    updated_doc = bump_doc(doc_text, current, args.new_version)

    if construct_text == updated_construct and doc_text == updated_doc:
        print("No files required updating; check your version inputs.")
        return

    write(CONSTRUCT, updated_construct)
    write(DOC, updated_doc)
    print(f"Bumped {current} -> {args.new_version}")


if __name__ == "__main__":
    main()
