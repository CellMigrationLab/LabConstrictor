#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONSTRUCT = ROOT / "construct.yaml"

# Match version line with optional quotes and optional trailing comment
VERSION_LINE_RE = re.compile(
    r'^(version:\s*)(?P<quote>["\']?)(?P<version>\d+\.\d+\.\d+)(?P=quote)(?P<trailing>\s*(?:#.*)?)$',
    re.MULTILINE,
)
THANKS_LINE_RE = re.compile(r'(Thank you for installing[^\n]* v)(\d+\.\d+\.\d+)(!)')


def read_current_version() -> tuple[str, str]:
    """Read construct.yaml as text and extract current SemVer.

    Returns (file_text, version_string). Exits if not found.
    """
    text = CONSTRUCT.read_text(encoding="utf-8")
    m = VERSION_LINE_RE.search(text)
    if not m:
        sys.exit("Could not find version in construct.yaml")
    return text, m.group("version")


def bump_construct_text(text: str, old_version: str, new_version: str) -> str:
    """Return updated file text with bumped version, preserving YAML structure/comments.

    - Updates the `version: "X.Y.Z"` line.
    - Updates the version inside the 'Thank you for installing ... vX.Y.Z!' line
      within `conclusion_text` if present.
    """
    # 1) Update the explicit version line
    def _repl_version(m: re.Match) -> str:
        # Preserve original quoting and trailing comment/whitespace
        return f"{m.group(1)}{m.group('quote')}{new_version}{m.group('quote')}{m.group('trailing')}"

    text = VERSION_LINE_RE.sub(_repl_version, text, count=1)

    # 2) Update the thank-you line version (only first occurrence)
    text = THANKS_LINE_RE.sub(lambda m: f"{m.group(1)}{new_version}{m.group(3)}", text, count=1)
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

    text, current = read_current_version()
    if args.new_version == current:
        print(f"Version already at {current}; nothing to update.")
        return

    updated_text = bump_construct_text(text, current, args.new_version)

    CONSTRUCT.write_text(updated_text, encoding="utf-8")
    print(f"Bumped {current} -> {args.new_version}")


if __name__ == "__main__":
    main()
