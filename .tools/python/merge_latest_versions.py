from pathlib import Path
import argparse
import yaml
import sys

def find_latest_version_files(source_dir: Path):
    if not source_dir.exists():
        return []
    return sorted(source_dir.rglob("latest_version.yaml"))


def main():
    parser = argparse.ArgumentParser(description="Merge multiple latest_version.yaml files into one.")
    parser.add_argument("--source-dir", default="notebooks", help="Directory to scan for latest_version.yaml files")
    parser.add_argument("--output", default="notebook_latest_versions.yaml", help="Output path to the yaml file to write")
    args = parser.parse_args()

    source = Path(args.source_dir)
    output = Path(args.output)

    print(f"Scanning {source} for latest_version.yaml files...")

    files = find_latest_version_files(source)
    if not files:
        print(f"No latest_version.yaml files found under {source}, writing empty {output}")
        return 0

    merged_latest_versions = {}

    for file_path in files:
        print(f"Processing {file_path}")

        notebook_folder = file_path.parent.name

        with open(file_path, 'r') as f:
            notebook_content = yaml.safe_load(f)

        merged_latest_versions[notebook_folder] = notebook_content

    with open(output, 'w', encoding='utf-8') as f:
        yaml.dump(merged_latest_versions, f)

if __name__ == "__main__":
    sys.exit(main())
