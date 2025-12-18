#!/usr/bin/env python3
"""
Fix files and directories with trailing spaces by renaming them.
"""

import os
from pathlib import Path
from typing import List, Tuple

def find_and_fix_trailing_spaces(root_dir: str, dry_run: bool = True) -> Tuple[int, int, List[str]]:
    """
    Find and fix all files/dirs with trailing spaces.

    Returns:
        (files_fixed, dirs_fixed, errors)
    """
    files_to_fix = []
    dirs_to_fix = []
    errors = []

    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"❌ Directory not found: {root_dir}")
        return 0, 0, [f"Root directory not found: {root_dir}"]

    print(f"🔍 Scanning: {root_dir}")
    print()

    # Walk the tree and collect all problematic entries
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Check filenames first (process files before their parent dirs)
        for filename in filenames:
            name_part = os.path.splitext(filename)[0]
            if name_part != name_part.rstrip():
                full_path = os.path.join(dirpath, filename)
                files_to_fix.append(full_path)

        # Check directory names (processed bottom-up due to topdown=False)
        for dirname in dirnames:
            if dirname != dirname.rstrip():
                full_path = os.path.join(dirpath, dirname)
                dirs_to_fix.append(full_path)

    total = len(files_to_fix) + len(dirs_to_fix)

    if total == 0:
        print("✅ No trailing spaces found!")
        return 0, 0, []

    print(f"📊 Found {total} entries to fix:")
    print(f"   - {len(files_to_fix)} files")
    print(f"   - {len(dirs_to_fix)} directories")
    print()

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

        if files_to_fix:
            print("=" * 80)
            print("FILES TO FIX")
            print("=" * 80)
            for path in files_to_fix[:10]:  # Show first 10
                old_name = os.path.basename(path)
                new_name = old_name.rstrip()
                print(f"  '{old_name}' → '{new_name}'")
            if len(files_to_fix) > 10:
                print(f"  ... and {len(files_to_fix) - 10} more files")
            print()

        if dirs_to_fix:
            print("=" * 80)
            print("DIRECTORIES TO FIX")
            print("=" * 80)
            for path in dirs_to_fix:
                old_name = os.path.basename(path)
                new_name = old_name.rstrip()
                print(f"  '{old_name}' → '{new_name}'")
            print()

        return 0, 0, []

    # Actually fix the entries
    files_fixed = 0
    dirs_fixed = 0

    print("🔧 Fixing files...")
    for old_path in files_to_fix:
        try:
            dirname = os.path.dirname(old_path)
            old_basename = os.path.basename(old_path)

            # Get name without extension, strip spaces, add extension back
            name_part, ext = os.path.splitext(old_basename)
            new_basename = name_part.rstrip() + ext
            new_path = os.path.join(dirname, new_basename)

            if old_path != new_path:
                os.rename(old_path, new_path)
                files_fixed += 1
                print(f"  ✓ Fixed: {old_basename} → {new_basename}")
        except Exception as e:
            error_msg = f"Failed to rename file: {old_path} - {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    print()
    print("🔧 Fixing directories...")
    for old_path in dirs_to_fix:
        try:
            dirname = os.path.dirname(old_path)
            old_basename = os.path.basename(old_path)
            new_basename = old_basename.rstrip()
            new_path = os.path.join(dirname, new_basename)

            if old_path != new_path:
                os.rename(old_path, new_path)
                dirs_fixed += 1
                print(f"  ✓ Fixed: {old_basename} → {new_basename}")
        except Exception as e:
            error_msg = f"Failed to rename directory: {old_path} - {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    return files_fixed, dirs_fixed, errors


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix files and directories with trailing spaces'
    )
    parser.add_argument(
        '--root',
        required=True,
        help='Root directory to scan and fix'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform the renames (default is dry-run)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("GHOST ENTRY FIXER")
    print("=" * 80)
    print(f"Root directory: {args.root}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 80)
    print()

    files_fixed, dirs_fixed, errors = find_and_fix_trailing_spaces(
        args.root,
        dry_run=not args.execute
    )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files fixed: {files_fixed}")
    print(f"Directories fixed: {dirs_fixed}")
    print(f"Errors: {len(errors)}")
    print("=" * 80)

    if errors:
        print()
        print("ERRORS:")
        for error in errors:
            print(f"  - {error}")

    if not args.execute and (files_fixed > 0 or dirs_fixed > 0 or errors):
        print()
        print("⚠️  This was a DRY RUN. No changes were made.")
        print("    Run with --execute to actually fix the entries.")


if __name__ == '__main__':
    main()
