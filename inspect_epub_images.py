#!/usr/bin/env python3
"""
Actually inspect what the images in an EPUB are
"""

import ebooklib
from ebooklib import epub
from pathlib import Path
import os

def inspect_images(epub_path):
    """List ALL images with their paths to see what we're dealing with."""
    book = epub.read_epub(epub_path)

    print(f"\n{'='*80}")
    print(f"EPUB: {Path(epub_path).name}")
    print(f"{'='*80}\n")

    images = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            images.append({
                'name': item.get_name(),
                'size': len(item.get_content())
            })

    print(f"Total images: {len(images)}\n")

    # Group by directory
    by_dir = {}
    for img in images:
        dirname = str(Path(img['name']).parent)
        if dirname not in by_dir:
            by_dir[dirname] = []
        by_dir[dirname].append(img)

    print(f"Images by directory:")
    for dirname, imgs in sorted(by_dir.items()):
        print(f"\n  {dirname}/ ({len(imgs)} images)")
        # Show first 10 from each directory
        for img in imgs[:10]:
            size_kb = img['size'] / 1024
            print(f"    - {Path(img['name']).name} ({size_kb:.1f} KB)")
        if len(imgs) > 10:
            print(f"    ... and {len(imgs) - 10} more")

if __name__ == '__main__':
    # Inspect the book with 587 images
    inspect_images("/Volumes/T7 Shield/books/epub/kotronias_0000_the_safest_scandinavian_reloaded.epub")

    # And the one with 797
    inspect_images("/Volumes/T7 Shield/books/epub/john_2012_play_the_french_everyman_chess.epub")
