#!/usr/bin/env python3
"""
Export removal lists for low-quality and corrupt files.
"""

import sqlite3
from pathlib import Path


def export_removal_lists(db_path: str = "epub_analysis.db"):
    """Generate removal lists from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. LOW tier EPUBs (score < 45)
    cursor.execute("""
        SELECT filename FROM epub_analysis
        WHERE tier = 'LOW' AND format = 'EPUB'
        ORDER BY score ASC
    """)
    low_epubs = [row[0] for row in cursor.fetchall()]

    # 2. LOW tier MOBIs (score < 45)
    cursor.execute("""
        SELECT filename FROM epub_analysis
        WHERE tier = 'LOW' AND format = 'MOBI'
        ORDER BY score ASC
    """)
    low_mobis = [row[0] for row in cursor.fetchall()]

    # 3. Corrupt/Error files
    cursor.execute("""
        SELECT filename FROM epub_analysis
        WHERE tier = 'ERROR'
        ORDER BY filename
    """)
    corrupt_files = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Write to files
    with open('remove_epub_low_quality.txt', 'w') as f:
        f.write('\n'.join(low_epubs) + '\n')

    with open('remove_mobi_low_quality.txt', 'w') as f:
        f.write('\n'.join(low_mobis) + '\n')

    with open('remove_corrupt_files.txt', 'w') as f:
        f.write('\n'.join(corrupt_files) + '\n')

    # Print summary
    print("=" * 80)
    print("REMOVAL LISTS GENERATED")
    print("=" * 80)
    print()

    print(f"📊 Summary Counts:")
    print(f"   {len(low_epubs)} EPUBs to remove (LOW tier)")
    print(f"   {len(low_mobis)} MOBIs to remove (LOW tier)")
    print(f"   {len(corrupt_files)} corrupt files to remove (ERROR)")
    print(f"   Total files to remove: {len(low_epubs) + len(low_mobis) + len(corrupt_files)}")
    print()

    # Show first 10 from each list
    print("=" * 80)
    print("PREVIEW: First 10 files from each list")
    print("=" * 80)
    print()

    if low_epubs:
        print(f"📕 Low Quality EPUBs ({len(low_epubs)} total):")
        for i, filename in enumerate(low_epubs[:10], 1):
            print(f"   {i:2d}. {filename}")
        if len(low_epubs) > 10:
            print(f"   ... and {len(low_epubs) - 10} more")
        print()

    if low_mobis:
        print(f"📙 Low Quality MOBIs ({len(low_mobis)} total):")
        for i, filename in enumerate(low_mobis[:10], 1):
            print(f"   {i:2d}. {filename}")
        if len(low_mobis) > 10:
            print(f"   ... and {len(low_mobis) - 10} more")
        print()

    if corrupt_files:
        print(f"❌ Corrupt/Error Files ({len(corrupt_files)} total):")
        for i, filename in enumerate(corrupt_files[:10], 1):
            print(f"   {i:2d}. {filename}")
        if len(corrupt_files) > 10:
            print(f"   ... and {len(corrupt_files) - 10} more")
        print()

    print("=" * 80)
    print("Files exported to:")
    print("  - remove_epub_low_quality.txt")
    print("  - remove_mobi_low_quality.txt")
    print("  - remove_corrupt_files.txt")
    print("=" * 80)


if __name__ == '__main__':
    export_removal_lists()
