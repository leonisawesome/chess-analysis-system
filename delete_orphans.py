#!/usr/bin/env python3
"""
Delete orphaned image directories (dirs without corresponding EPUBs).
"""
import hashlib
import subprocess
from pathlib import Path

epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
images_dir = Path("/Volumes/T7 Shield/rag/books/images")

# Get valid book IDs from EPUBs
epub_files = [f for f in epub_dir.glob("*.epub") if not f.name.startswith('._')]
valid_book_ids = {f"book_{hashlib.md5(f.stem.encode()).hexdigest()[:12]}" for f in epub_files}

# Find orphaned directories
image_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
orphaned = [d for d in image_dirs if d.name not in valid_book_ids]

print(f"Valid EPUBs: {len(epub_files)}")
print(f"Image directories: {len(image_dirs)}")
print(f"Orphaned directories: {len(orphaned)}\n")

if not orphaned:
    print("✓ No orphaned directories to delete")
    exit(0)

print("=" * 80)
print("DELETING ORPHANED DIRECTORIES")
print("=" * 80)

for orphan_dir in orphaned:
    image_count = len(list(orphan_dir.glob("*")))
    print(f"\n{orphan_dir.name}")
    print(f"  Images: {image_count}")

    # Delete directory
    subprocess.run(['rm', '-rf', str(orphan_dir)], check=True)
    print(f"  ✓ Deleted")

# Verify
remaining_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
print(f"\n{'=' * 80}")
print(f"Final count: {len(remaining_dirs)} directories")
print(f"Expected: {len(epub_files)}")

if len(remaining_dirs) <= len(epub_files):
    print("✓ Orphans cleaned up successfully")
else:
    print(f"⚠ Still have {len(remaining_dirs) - len(epub_files)} extra directories")
