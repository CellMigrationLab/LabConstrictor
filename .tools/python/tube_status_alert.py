import sys
import yaml
import subprocess

def get_git_file(rev, filepath):
    try:
        out = subprocess.check_output(['git', 'show', f'{rev}:{filepath}'])
        return out.decode()
    except subprocess.CalledProcessError:
        return ""

def compare_files(before_sha, after_sha, files):
    payload = []
    for f in files:
        old = get_git_file(before_sha, f)
        new = get_git_file(after_sha, f)
        bef = yaml.safe_load(old or "{}")
        aft = yaml.safe_load(new or "{}")
        bef_list = bef.get("antibodies", bef if isinstance(bef, list) else [])
        aft_list = aft.get("antibodies", aft if isinstance(aft, list) else [])
        bef_map = {e["antibody_name"]: e.get("status", {}).get("tube") for e in bef_list}
        old_names = set(bef_map)
        for e in aft_list:
            nm = e["antibody_name"]
            old_s = bef_map.get(nm)
            new_s = e.get("status", {}).get("tube")
            if nm not in old_names:
                if new_s == "available":
                    payload.append(f"New antibody available: {nm} in {f}")
            if new_s == "empty" and old_s != "empty":
                payload.append(f":warning: *EMPTY:* `{nm}` in `{f}`")
            if old_s == "empty" and new_s != "empty":
                payload.append(f":white_check_mark: *BACK IN STOCK:* `{nm}` in `{f}`")


    return payload

def main():
    if len(sys.argv) < 4:
        print("Usage: python tube_status_alert.py <before_sha> <after_sha> <file1> [<file2> ...]", file=sys.stderr)
        sys.exit(1)
    before_sha = sys.argv[1]
    after_sha = sys.argv[2]
    files = sys.argv[3:]
    alerts = compare_files(before_sha, after_sha, files)
    if alerts:
        print("\n".join(alerts))
    else:
        sys.exit(78)  # For GitHub Actions, exit code 78 = neutral

if __name__ == "__main__":
    main()
