import json
import sys
from pathlib import Path


def build_notebook_list(notebooks_root: Path):
	items = []
	for ipynb in notebooks_root.rglob("*.ipynb"):
		# Path relative to notebooks folder
		rel = ipynb.relative_to(notebooks_root)
		name = ipynb.stem
		items.append({
			"name": name,
			"description": "-",
			"path": str(rel).replace("\\", "/"),
		})
	# Sort for deterministic order
	items.sort(key=lambda x: x["path"]) 
	return items


def populate_template(template_path: Path, output_path: Path, owner: str, repo: str, notebooks_root: Path):
	data = json.loads(template_path.read_text(encoding="utf-8"))

	# Generate notebooks list
	notebooks_list = build_notebook_list(notebooks_root)

	# Replace in cells: GITHUB_OWNER, GITHUB_REPO_NAME, and DICT_OF_NOTEBOOKS
	for cell in data.get("cells", []):
		if cell.get("cell_type") == "code":
			# Replace owner/repo placeholders
			new_source = []
			for line in cell.get("source", []):
				line = line.replace("GITHUB_OWNER", owner)
				line = line.replace("GITHUB_REPO_NAME", repo)
				# Replace notebooks = DICT_OF_NOTEBOOKS with concrete list
				if "notebooks = DICT_OF_NOTEBOOKS" in line:
					line = "notebooks = " + json.dumps(notebooks_list, ensure_ascii=False)
				new_source.append(line)
			cell["source"] = new_source

	output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
	# Args: owner repo [template_path] [output_path]
	if len(sys.argv) < 3:
		print("Usage: populate_Welcome_notebook.py <owner> <repo> [template] [output]", file=sys.stderr)
		sys.exit(1)

	owner = sys.argv[1]
	repo = sys.argv[2]

	template_path = Path(".tools/templates/Welcome_template.ipynb")
	output_path = Path("app/menuinst/Welcome.ipynb")
	notebooks_root = Path("notebooks").resolve()

	output_path.parent.mkdir(parents=True, exist_ok=True)

	populate_template(template_path, output_path, owner, repo, notebooks_root)
	print(f"Populated Welcome notebook written to: {output_path}")


if __name__ == "__main__":
	main()

