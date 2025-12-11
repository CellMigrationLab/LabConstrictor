import subprocess
from collections import defaultdict
from pathlib import Path
import sys

OUTPUT_FILE = Path('docs/leaderboard.md')

def get_contributors():
    """Return a set of all contributor names who have touched the lab_database/ directory."""
    result = subprocess.run(
        ['git', 'log', '--format=%an', '--', 'lab_database'],
        capture_output=True, text=True, check=True
    )
    return set(line.strip() for line in result.stdout.splitlines() if line.strip())

def get_author_stats(author):
    """Return (commit count, line changes) for a specific author in lab_database/."""
    # Get commit count
    count_result = subprocess.run(
        [
            'git', 'log', '--no-merges', '--pretty=%H',
            '--author', author, '--', 'lab_database'
        ],
        capture_output=True, text=True, check=True
    )
    commit_count = len([h for h in count_result.stdout.splitlines() if h.strip()])

    # Get line changes
    numstat_result = subprocess.run(
        [
            'git', 'log', '--no-merges', '--numstat',
            '--author', author, '--pretty=format:',
            '--', 'lab_database'
        ],
        capture_output=True, text=True, check=True
    )
    total_changes = 0
    for line in numstat_result.stdout.splitlines():
        if '\t' not in line:
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            continue
        try:
            added = int(parts[0])
        except ValueError:
            added = 0
        try:
            removed = int(parts[1])
        except ValueError:
            removed = 0
        total_changes += added + removed

    return commit_count, total_changes

def main():
    contributors = get_contributors()
    stats = {}
    for author in contributors:
        commit_count, line_changes = get_author_stats(author)
        stats[author] = (commit_count, line_changes)
        print(f"INFO: {author}: {commit_count} commits, {line_changes} line changes", file=sys.stderr)

    lines = [
        '# Contributor Leaderboard',
        '',
        'This leaderboard ranks contributors by total commits and total line changes in the [lab_database directory](../lab_database/).',
        '',
        '| Author | Commits | Line Changes |',
        '|--------|---------|--------------|'
    ]
    if not stats:
        lines.append('| _No contributors found_ | 0 | 0 |')
    else:
        for author, (commits, lines_changed) in sorted(
            stats.items(), key=lambda x: (x[1][1], x[1][0]), reverse=True
        ):
            lines.append(f'| {author} | {commits} | {lines_changed} |')

    lines.extend(
        [
            '',
            '## Generate in a Notebook',
            '',
            'Run the following cell in a Jupyter notebook to compute the leaderboard on demand:',
            '',
            '```python',
            'import subprocess',
            'import pandas as pd',
            '',
            "def get_author_stats(author):",
            "    count_result = subprocess.run([",
            "        'git', 'log', '--no-merges', '--pretty=%H',",
            "        '--author', author, '--', 'lab_database'",
            "    ], capture_output=True, text=True, check=True)",
            "    commit_count = len([h for h in count_result.stdout.splitlines() if h.strip()])",
            "",
            "    numstat_result = subprocess.run([",
            "        'git', 'log', '--no-merges', '--numstat',",
            "        '--author', author, '--pretty=format:', '--', 'lab_database'",
            "    ], capture_output=True, text=True, check=True)",
            "    total_changes = 0",
            "    for line in numstat_result.stdout.splitlines():",
            "        if '\\t' not in line:",
            "            continue",
            "        parts = line.split('\\t')",
            "        if len(parts) < 3:",
            "            continue",
            "        try: added = int(parts[0])",
            "        except ValueError: added = 0",
            "        try: removed = int(parts[1])",
            "        except ValueError: removed = 0",
            "        total_changes += added + removed",
            "    return commit_count, total_changes",
            "",
            "contributors = subprocess.run(['git', 'log', '--format=%an', '--', 'lab_database'], capture_output=True, text=True, check=True).stdout.splitlines()",
            "contributors = set(c.strip() for c in contributors if c.strip())",
            "data = [(c, *get_author_stats(c)) for c in contributors]",
            "df = pd.DataFrame(sorted(data, key=lambda x: (x[2], x[1]), reverse=True), columns=['Author', 'Commits', 'Line Changes'])",
            "df",
            '```',
            '',
            'This outputs a table ranking contributors by their total commits and total line changes in the [lab_database directory](../lab_database/).'
        ]
    )

    OUTPUT_FILE.write_text('\n'.join(lines) + '\n')

if __name__ == '__main__':
    main()
