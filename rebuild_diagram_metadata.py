#!/usr/bin/env python3
"""
Rebuild diagram_metadata_full.json from extracted diagrams on disk.

This scans all book directories in /Volumes/T7 Shield/rag/books/images/
and creates a complete metadata file without re-extracting.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

IMAGES_DIR = Path("/Volumes/T7 Shield/rag/books/images")
OUTPUT_FILE = "diagram_metadata_full.json"

def get_image_info(image_path):
    """Extract metadata from a single image file."""
    stat = os.stat(image_path)
    return {
        'diagram_id': image_path.stem,
        'book_id': image_path.parent.name,
        'file_path': str(image_path),
        'format': image_path.suffix[1:].upper(),  # .png -> PNG
        'size_bytes': stat.st_size,
        # Note: We don't have context_before/after without re-parsing EPUBs
        # But that's OK - the diagram service only needs basic metadata
        'epub_filename': 'unknown',  # Will be populated from book_id mapping
        'position_in_document': int(image_path.stem.split('_')[-1])  # Extract number from filename
    }

def main():
    print("Scanning extracted diagram directories...")
    print(f"Base directory: {IMAGES_DIR}")

    if not IMAGES_DIR.exists():
        print(f"ERROR: Directory not found: {IMAGES_DIR}")
        print("Is the external drive mounted?")
        return

    # Get all book directories
    book_dirs = sorted([d for d in IMAGES_DIR.iterdir() if d.is_dir() and d.name.startswith('book_')])
    print(f"Found {len(book_dirs)} book directories")

    if len(book_dirs) == 0:
        print("ERROR: No book directories found!")
        return

    # Collect all diagrams
    all_diagrams = []
    stats = {
        'total_books': len(book_dirs),
        'books_processed': 0,
        'total_diagrams': 0,
        'total_size_bytes': 0,
        'by_format': defaultdict(int),
        'books': []
    }

    print("\nScanning diagrams from each book...")
    for book_dir in tqdm(book_dirs, desc="Processing books"):
        try:
            # Get all image files in this book directory
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
                image_files.extend(book_dir.glob(ext))

            if not image_files:
                continue

            # Sort by filename to maintain order
            image_files = sorted(image_files)

            book_diagrams = []
            for img_file in image_files:
                try:
                    diagram_info = get_image_info(img_file)
                    book_diagrams.append(diagram_info)

                    # Update stats
                    stats['total_size_bytes'] += diagram_info['size_bytes']
                    stats['by_format'][diagram_info['format']] += 1

                except Exception as e:
                    print(f"Warning: Error processing {img_file}: {e}")
                    continue

            if book_diagrams:
                all_diagrams.extend(book_diagrams)
                stats['books_processed'] += 1
                stats['total_diagrams'] += len(book_diagrams)
                stats['books'].append({
                    'book_id': book_dir.name,
                    'diagram_count': len(book_diagrams)
                })

        except Exception as e:
            print(f"Error processing book directory {book_dir}: {e}")
            continue

    # Convert defaultdict to regular dict for JSON serialization
    stats['by_format'] = dict(stats['by_format'])

    # Create metadata structure
    metadata = {
        'stats': stats,
        'diagrams': all_diagrams
    }

    # Save to file
    print(f"\nSaving metadata to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Print summary
    print("\n" + "="*80)
    print("METADATA REBUILD COMPLETE")
    print("="*80)
    print(f"Books processed: {stats['books_processed']}/{stats['total_books']}")
    print(f"Total diagrams: {stats['total_diagrams']:,}")
    print(f"Total size: {stats['total_size_bytes'] / (1024**3):.2f} GB")
    print(f"\nBy format:")
    for fmt, count in sorted(stats['by_format'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {fmt}: {count:,} ({count/stats['total_diagrams']*100:.1f}%)")
    print(f"\nOutput file: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE) / (1024**2):.1f} MB)")
    print("="*80)

if __name__ == '__main__':
    main()
