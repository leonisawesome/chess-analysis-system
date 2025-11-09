#!/usr/bin/env python3
"""
EPUB Diagram Audit Script
Examines EPUB files to understand how diagrams are encoded and structured.
"""

import sys
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
from collections import defaultdict

def audit_epub_images(epub_path):
    """
    Audit a single EPUB file for images.

    Returns dict with:
    - total_images: count
    - image_formats: {format: count}
    - image_sizes: {image_name: size_bytes}
    - image_references: where images are used in text
    """
    try:
        book = epub.read_epub(epub_path)

        result = {
            'file': Path(epub_path).name,
            'total_images': 0,
            'image_formats': defaultdict(int),
            'image_details': [],
            'html_references': [],
            'text_chunks_with_images': 0
        }

        # Get all images
        images = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                images.append(item)

                # Get format from file extension
                img_name = item.get_name()
                ext = Path(img_name).suffix.lower()
                result['image_formats'][ext] += 1

                # Get size
                content = item.get_content()
                size = len(content)

                result['image_details'].append({
                    'name': img_name,
                    'format': ext,
                    'size': size,
                    'size_kb': round(size / 1024, 2)
                })

        result['total_images'] = len(images)

        # Examine HTML/XHTML to see how images are referenced
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')

                # Find all img tags
                img_tags = soup.find_all('img')
                if img_tags:
                    result['text_chunks_with_images'] += 1

                    for img_tag in img_tags:
                        src = img_tag.get('src', '')
                        alt = img_tag.get('alt', '')

                        # Get surrounding text (before and after)
                        parent = img_tag.parent

                        # Get all text from the parent element
                        if parent:
                            # Get text before image
                            preceding = []
                            for prev in img_tag.find_all_previous(string=True):
                                if prev.parent == parent:
                                    preceding.append(str(prev))
                                if len(' '.join(preceding)) > 300:
                                    break

                            # Get text after image
                            following = []
                            for next_elem in img_tag.find_all_next(string=True):
                                if next_elem.parent == parent:
                                    following.append(str(next_elem))
                                if len(' '.join(following)) > 300:
                                    break

                            before = ' '.join(reversed(preceding)).strip()[-150:]
                            after = ' '.join(following).strip()[:150]
                            context = f"...{before} [IMAGE] {after}..."
                        else:
                            context = '[No context]'

                        result['html_references'].append({
                            'src': src,
                            'alt': alt,
                            'context': context.strip()
                        })

        return result

    except Exception as e:
        return {
            'file': Path(epub_path).name,
            'error': str(e)
        }

def print_audit_results(result):
    """Print audit results in readable format."""
    print(f"\n{'='*80}")
    print(f"EPUB: {result['file']}")
    print(f"{'='*80}")

    if 'error' in result:
        print(f"❌ ERROR: {result['error']}")
        return

    print(f"\n📊 IMAGE STATISTICS:")
    print(f"  Total Images: {result['total_images']}")
    print(f"  Text Chunks with Images: {result['text_chunks_with_images']}")

    print(f"\n📁 IMAGE FORMATS:")
    for fmt, count in sorted(result['image_formats'].items()):
        print(f"  {fmt}: {count} images")

    if result['image_details']:
        print(f"\n📷 SAMPLE IMAGES (first 5):")
        for img in result['image_details'][:5]:
            print(f"  • {img['name']}")
            print(f"    Format: {img['format']}, Size: {img['size_kb']} KB")

    if result['html_references']:
        print(f"\n🔗 IMAGE REFERENCES (first 3):")
        for ref in result['html_references'][:3]:
            print(f"  • SRC: {ref['src']}")
            print(f"    ALT: {ref['alt']}")
            print(f"    Context: {ref['context'][:100]}...")
            print()

def main():
    # Sample books to audit (diagram-heavy ones preferred)
    sample_books = [
        "/Volumes/T7 Shield/epub/kotronias_0000_the_safest_scandinavian_reloaded.epub",
        "/Volumes/T7 Shield/epub/john_2012_play_the_french_everyman_chess.epub",
        "/Volumes/T7 Shield/epub/simeonidis_2020_carlsens_neo_moller_nic.epub",
    ]

    print("🔍 EPUB Diagram Audit - Examining diagram encoding in chess books")
    print("="*80)

    all_results = []

    for epub_path in sample_books:
        if not Path(epub_path).exists():
            print(f"\n⚠️  File not found: {epub_path}")
            continue

        print(f"\nProcessing: {Path(epub_path).name}...")
        result = audit_epub_images(epub_path)
        all_results.append(result)
        print_audit_results(result)

    # Summary
    print(f"\n{'='*80}")
    print("📋 SUMMARY ACROSS ALL BOOKS")
    print(f"{'='*80}")

    total_images = sum(r.get('total_images', 0) for r in all_results if 'error' not in r)
    total_chunks = sum(r.get('text_chunks_with_images', 0) for r in all_results if 'error' not in r)

    print(f"Books Audited: {len(all_results)}")
    print(f"Total Images Found: {total_images}")
    print(f"Text Chunks with Images: {total_chunks}")

    # Aggregate formats
    all_formats = defaultdict(int)
    for r in all_results:
        if 'error' not in r:
            for fmt, count in r['image_formats'].items():
                all_formats[fmt] += count

    print(f"\nImage Formats Across All Books:")
    for fmt, count in sorted(all_formats.items()):
        print(f"  {fmt}: {count} images")

if __name__ == '__main__':
    main()
