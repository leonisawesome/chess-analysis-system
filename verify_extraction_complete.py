#!/usr/bin/env python3
"""
Simple verification: Do all 920 EPUBs have corresponding image directories?
"""
import hashlib
from pathlib import Path

epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
images_dir = Path("/Volumes/T7 Shield/rag/books/images")

# Get all EPUBs
epub_files = sorted([f for f in epub_dir.glob("*.epub") if not f.name.startswith('._')])
print(f"Total EPUBs: {len(epub_files)}\n")

# Check each EPUB for corresponding directory
missing = []
present = []

for epub_path in epub_files:
    book_id = f"book_{hashlib.md5(epub_path.stem.encode()).hexdigest()[:12]}"
    img_dir = images_dir / book_id

    if img_dir.exists():
        present.append((epub_path.name, book_id))
    else:
        missing.append((epub_path.name, book_id))

print(f"✓ EPUBs with image directories: {len(present)}")
print(f"✗ EPUBs missing image directories: {len(missing)}\n")

if missing:
    print("=" * 80)
    print("MISSING IMAGE DIRECTORIES")
    print("=" * 80)
    for epub_name, book_id in missing[:10]:  # Show first 10
        print(f"{book_id} -> {epub_name}")
    if len(missing) > 10:
        print(f"... and {len(missing) - 10} more")
else:
    print("✓ SUCCESS: All 920 EPUBs have image directories!")

# Count total directories
all_dirs = [d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
print(f"\nTotal image directories: {len(all_dirs)}")
print(f"Expected (from EPUBs): {len(epub_files)}")

if len(all_dirs) > len(epub_files):
    print(f"Orphaned directories: {len(all_dirs) - len(epub_files)}")
