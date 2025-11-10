#!/usr/bin/env python3
"""
Identify orphaned image directories by comparing EPUB book IDs with directory names.
Uses the exact same book ID generation method as extract_epub_diagrams.py
"""
import hashlib
from pathlib import Path

epub_dir = Path("/Volumes/T7 Shield/books/epub")
images_dir = Path("/Volumes/T7 Shield/books/images")

# Get all EPUBs (excluding Mac metadata files)
epub_files = [f for f in epub_dir.glob("*.epub") if not f.name.startswith('._')]
print(f"EPUB files: {len(epub_files)}")

# Generate book IDs using the EXACT method from extract_epub_diagrams.py
# NOTE: Uses epub_path.stem (filename without .epub extension)
valid_book_ids = set()
for epub_path in epub_files:
    book_id = f"book_{hashlib.md5(epub_path.stem.encode()).hexdigest()[:12]}"
    valid_book_ids.add(book_id)

print(f"Valid book IDs: {len(valid_book_ids)}")

# Get all image directories
image_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
print(f"Image directories: {len(image_dirs)}")

# Find orphaned directories
orphaned = []
for img_dir in image_dirs:
    if img_dir.name not in valid_book_ids:
        orphaned.append(img_dir)

print(f"\nOrphaned directories: {len(orphaned)}\n")

if orphaned:
    print("=" * 80)
    print("ORPHANED DIRECTORIES")
    print("=" * 80)
    for orphan in orphaned:
        image_count = len(list(orphan.glob("*")))
        print(f"\n{orphan.name}")
        print(f"  Images: {image_count}")
        print(f"  Path: {orphan}")
else:
    print("✓ No orphaned directories found!")
