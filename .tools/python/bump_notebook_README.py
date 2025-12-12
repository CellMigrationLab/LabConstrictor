from pathlib import Path
import sys
import os

def list_notebooks(base_dir: Path):
	for p in base_dir.rglob("*.ipynb"):
		yield p


def notebooks_from_changed_files(changed_files: list[str], base_dir: Path):
	result = []
	for f in changed_files:
		fp = (base_dir / f).resolve() if not f.startswith(str(base_dir)) else Path(f).resolve()
		if fp.suffix == ".ipynb" and base_dir in fp.parents:
			result.append(fp)
	return result


def build_readme_content(notebook_path: Path) -> str:
	rel = notebook_path.relative_to(notebook_path.parents[1]) if len(notebook_path.parts) > 2 else notebook_path.name
	title = notebook_path.stem.replace("_", " ")
	lines = [
		f"# {title}",
		"",
		"This folder contains a Jupyter notebook.",
		"",
		"## Notebook",
		f"- File: {notebook_path.name}",
	]
	return "\n".join(lines) + "\n"


def write_readme_for_notebook(notebook_path: Path):
	folder = notebook_path.parent
	readme_path = folder / "README.md"
	content = build_readme_content(notebook_path)
	readme_path.write_text(content, encoding="utf-8")


def main():
	base_dir = Path("notebooks").resolve()
	if not base_dir.exists():
		print("notebooks directory not found", file=sys.stderr)
		sys.exit(1)

	# Accept changed files via CLI args or env var
	changed_arg = sys.argv[1:]  # list of paths
	changed_env = os.environ.get("CHANGED_NOTEBOOKS", "")
	changed_files = []
	if changed_arg:
		changed_files = changed_arg
	elif changed_env:
		# Split on newlines or spaces
		if "\n" in changed_env:
			changed_files = [s for s in changed_env.split("\n") if s.strip()]
		else:
			changed_files = [s for s in changed_env.split(" ") if s.strip()]

	if changed_files:
		print(f"Received changed files ({len(changed_files)}):")
		for f in changed_files:
			print(f"  - {f}")
		notebooks = notebooks_from_changed_files(changed_files, base_dir)
		print(f"Filtered to notebooks in '{base_dir.name}' ({len(notebooks)}):")
		for nb in notebooks:
			print(f"  - {nb}")
	else:
		print("No changed files provided; scanning all notebooks...")
		notebooks = list(list_notebooks(base_dir))
		print(f"Found {len(notebooks)} notebooks under '{base_dir}':")
		for nb in notebooks:
			print(f"  - {nb}")

	# Deduplicate
	notebooks = sorted(set(notebooks))

	updated = 0
	for nb in notebooks:
		write_readme_for_notebook(nb)
		updated += 1
		print(f"Updated README: {nb.parent / 'README.md'}")

	print(f"Completed README generation for {updated} notebook(s).")


if __name__ == "__main__":
	main()

