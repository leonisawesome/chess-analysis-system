#!/usr/bin/env python3
"""
Find files and directories with trailing spaces that cause access issues.
"""

import os
from pathlib import Path

def find_trailing_space_entries(root_dir):
    """Find all files/dirs with trailing spaces in their names."""
    problematic = []

    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"❌ Directory not found: {root_dir}")
        return []

    print(f"🔍 Scanning: {root_dir}")
    print()

    # Walk the entire tree
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Check directory names for trailing spaces
        for dirname in dirnames:
            if dirname != dirname.rstrip():
                full_path = os.path.join(dirpath, dirname)
                problematic.append({
                    'type': 'directory',
                    'path': full_path,
                    'name': dirname
                })

        # Check filenames for trailing spaces (before extension)
        for filename in filenames:
            # Check if name (without extension) has trailing space
            name_part = os.path.splitext(filename)[0]
            if name_part != name_part.rstrip():
                full_path = os.path.join(dirpath, filename)
                problematic.append({
                    'type': 'file',
                    'path': full_path,
                    'name': filename
                })

    return problematic

def main():
    root = "/Volumes/chess/1Chessable"

    entries = find_trailing_space_entries(root)

    print("=" * 80)
    print("GHOST ENTRIES WITH TRAILING SPACES")
    print("=" * 80)
    print()

    if not entries:
        print("✅ No ghost entries found!")
        return

    # Separate by type
    dirs = [e for e in entries if e['type'] == 'directory']
    files = [e for e in entries if e['type'] == 'file']

    print(f"📊 Total: {len(entries)} ghost entries")
    print(f"   - {len(dirs)} directories")
    print(f"   - {len(files)} files")
    print()

    if dirs:
        print("=" * 80)
        print("DIRECTORIES WITH TRAILING SPACES")
        print("=" * 80)
        for entry in dirs:
            print(f"  {entry['path']}")
        print()

    if files:
        print("=" * 80)
        print("FILES WITH TRAILING SPACES")
        print("=" * 80)
        for entry in files:
            print(f"  {entry['path']}")
        print()

if __name__ == '__main__':
    main()
