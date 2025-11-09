#!/usr/bin/env python3
"""
Examine EPUB HTML structure to understand diagram placement
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path

def examine_epub_html(epub_path):
    """Look at actual HTML structure of an EPUB."""
    print(f"\n{'='*80}")
    print(f"Examining: {Path(epub_path).name}")
    print(f"{'='*80}\n")

    book = epub.read_epub(epub_path)

    # Find first HTML document with images
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')

            img_tags = soup.find_all('img')
            if img_tags and len(img_tags) >= 3:
                print(f"📄 Document: {item.get_name()}")
                print(f"Found {len(img_tags)} images in this document\n")

                # Show first 3 images with full parent context
                for i, img in enumerate(img_tags[:3], 1):
                    print(f"\n{'─'*80}")
                    print(f"IMAGE #{i}")
                    print(f"{'─'*80}")
                    print(f"SRC: {img.get('src', 'N/A')}")
                    print(f"ALT: {img.get('alt', 'N/A')}")

                    # Get parent element
                    parent = img.parent
                    print(f"\nParent Tag: <{parent.name}>")

                    # Get all text content from parent
                    parent_text = parent.get_text(separator=' ', strip=True)
                    print(f"\nParent Text Content ({len(parent_text)} chars):")
                    print(f"{parent_text[:500]}...")

                    # Show grandparent too
                    if parent.parent:
                        grandparent = parent.parent
                        grandparent_text = grandparent.get_text(separator=' ', strip=True)
                        print(f"\nGrandparent Tag: <{grandparent.name}>")
                        print(f"Grandparent Text ({len(grandparent_text)} chars):")
                        print(f"{grandparent_text[:500]}...")

                # Also show raw HTML snippet
                print(f"\n{'─'*80}")
                print("RAW HTML SNIPPET (with first image):")
                print(f"{'─'*80}")
                # Find the part of HTML with first image
                html_str = str(soup)
                img_src = img_tags[0].get('src', '')
                if img_src:
                    idx = html_str.find(img_src)
                    if idx > 0:
                        start = max(0, idx - 300)
                        end = min(len(html_str), idx + 300)
                        print(html_str[start:end])

                break  # Only examine first document with images

if __name__ == '__main__':
    # Examine one book
    epub_file = "/Volumes/T7 Shield/epub/simeonidis_2020_carlsens_neo_moller_nic.epub"
    examine_epub_html(epub_file)
