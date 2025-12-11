#!/usr/bin/env python3
"""
Process construct.yaml to expand folder paths and wildcards in extra_files.

This script reads construct.yaml, expands any folder paths or wildcards in the
extra_files field into individual file mappings, and writes the processed
version to a new file that can be used by conda-constructor.

Usage:
    python process_construct.py [input_file] [output_file]
    
    Defaults:
        input_file: construct.yaml
        output_file: construct_processed.yaml
"""

import sys
from pathlib import Path
import yaml


def expand_extra_files(extra_files, base_dir):
    """
    Expand folder paths and wildcards in extra_files to individual file mappings.
    
    Args:
        extra_files: List of file paths or mappings from construct.yaml
        base_dir: Base directory to resolve relative paths
        
    Returns:
        List of expanded file mappings
    """
    expanded = []
    
    for entry in extra_files:
        if isinstance(entry, str):
            # Simple string path
            source = Path(base_dir) / entry
            if source.is_dir():
                # Expand directory to all files
                for file_path in source.rglob('*'):
                    if file_path.is_file():
                        relative = file_path.relative_to(base_dir)
                        expanded.append(str(relative))
            elif '*' in entry:
                # Handle wildcards
                parts = entry.split('/')
                if '*' in parts[-1]:
                    # Wildcard in filename
                    parent = Path(base_dir) / '/'.join(parts[:-1])
                    pattern = parts[-1]
                    for file_path in parent.glob(pattern):
                        if file_path.is_file():
                            relative = file_path.relative_to(base_dir)
                            expanded.append(str(relative))
                else:
                    # Wildcard in path (e.g., dir/*/file.txt)
                    for file_path in Path(base_dir).glob(entry):
                        if file_path.is_file():
                            relative = file_path.relative_to(base_dir)
                            expanded.append(str(relative))
            else:
                # Regular file
                expanded.append(entry)
                
        elif isinstance(entry, dict):
            # Mapping: {source: destination}
            for source, dest in entry.items():
                source_path = Path(base_dir) / source
                
                if source_path.is_dir():
                    # Expand directory
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            relative_to_source = file_path.relative_to(source_path)
                            dest_path = Path(dest) / relative_to_source
                            expanded.append({str(file_path.relative_to(base_dir)): str(dest_path)})
                            
                elif '*' in source:
                    # Handle wildcards in source
                    matched_files = list(Path(base_dir).glob(source))
                    
                    if '*' in dest:
                        # Both source and dest have wildcards - preserve structure
                        for file_path in matched_files:
                            if file_path.is_file():
                                relative = file_path.relative_to(base_dir)
                                # Replace wildcard in dest with actual path
                                dest_resolved = dest.replace('*', file_path.name)
                                expanded.append({str(relative): dest_resolved})
                    else:
                        # Only source has wildcard
                        dest_path = Path(dest)
                        for file_path in matched_files:
                            if file_path.is_file():
                                relative = file_path.relative_to(base_dir)
                                # If dest is a directory, preserve filename
                                if dest.endswith('/'):
                                    final_dest = dest_path / file_path.name
                                else:
                                    final_dest = dest_path / file_path.relative_to(Path(base_dir) / source.split('*')[0].rstrip('/'))
                                expanded.append({str(relative): str(final_dest)})
                else:
                    # Regular file mapping
                    expanded.append(entry)
    
    return expanded


def process_construct_yaml(input_file, output_file):
    """
    Process construct.yaml to expand extra_files entries.
    
    Args:
        input_file: Path to input construct.yaml
        output_file: Path to output processed construct.yaml
    """
    input_path = Path(input_file)
    base_dir = input_path.parent
    
    # Read the construct.yaml
    with open(input_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Expand extra_files if present
    if 'extra_files' in config:
        print(f"Original extra_files entries: {len(config['extra_files'])}")
        config['extra_files'] = expand_extra_files(config['extra_files'], base_dir)
        print(f"Expanded extra_files entries: {len(config['extra_files'])}")
    
    # Write the processed config
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"Processed construct.yaml written to: {output_file}")


def main():
    """Main entry point."""
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'construct.yaml'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'construct_processed.yaml'
    
    process_construct_yaml(input_file, output_file)


if __name__ == '__main__':
    main()
