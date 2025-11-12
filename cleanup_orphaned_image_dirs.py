#!/usr/bin/env python3
"""
Find and delete orphaned image directories (dirs without corresponding EPUBs).

Current state:
- 920 EPUB files
- 938 image directories
- 18 orphaned directories need cleanup
"""
import hashlib
import subprocess
from pathlib import Path
from typing import Set

epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
images_dir = Path("/Volumes/T7 Shield/rag/books/images")

print("=" * 80)
print("CLEANING UP ORPHANED IMAGE DIRECTORIES")
print("=" * 80)

# Step 1: Get all valid book_ids from existing EPUBs
print("\n1. Scanning EPUB files...")
epub_files = [f for f in epub_dir.glob("*.epub") if not f.name.startswith('._')]
print(f"   Found {len(epub_files)} EPUB files")

valid_book_ids: Set[str] = set()
for epub_path in epub_files:
    book_id = f"book_{hashlib.md5(epub_path.name.encode()).hexdigest()[:12]}"
    valid_book_ids.add(book_id)

print(f"   Generated {len(valid_book_ids)} valid book IDs")

# Step 2: Find all image directories
print("\n2. Scanning image directories...")
image_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
print(f"   Found {len(image_dirs)} image directories")

# Step 3: Identify orphaned directories
print("\n3. Finding orphaned directories...")
orphaned_dirs = []
for img_dir in image_dirs:
    if img_dir.name not in valid_book_ids:
        orphaned_dirs.append(img_dir)

print(f"   Found {len(orphaned_dirs)} orphaned directories\n")

if not orphaned_dirs:
    print("✓ No orphaned directories found - collection is clean!")
    exit(0)

# Step 4: Delete orphaned directories
print("=" * 80)
print("DELETING ORPHANED DIRECTORIES")
print("=" * 80)

for orphan_dir in orphaned_dirs:
    # Count images in directory
    image_count = len(list(orphan_dir.glob("*")))

    print(f"\nDeleting: {orphan_dir.name}")
    print(f"  Images: {image_count}")

    # Delete directory
    subprocess.run(['rm', '-rf', str(orphan_dir)], check=True)
    print(f"  ✓ Deleted")

# Step 5: Verify final state
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

remaining_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
print(f"EPUB files: {len(epub_files)}")
print(f"Image directories: {len(remaining_dirs)}")

if len(epub_files) == len(remaining_dirs):
    print("\n✓ SUCCESS: EPUB count matches image directory count!")
else:
    print(f"\n⚠ WARNING: Still have mismatch!")
    print(f"  Difference: {abs(len(epub_files) - len(remaining_dirs))} directories")
