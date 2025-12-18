#!/usr/bin/env python3
"""
Count how many images are in each HTML document
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path

def count_images_per_doc(epub_path):
    """Count images per HTML document."""
    book = epub.read_epub(epub_path)

    print(f"\n{'='*80}")
    print(f"EPUB: {Path(epub_path).name}")
    print(f"{'='*80}\n")

    doc_image_counts = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')

            img_tags = soup.find_all('img')
            if img_tags:
                doc_image_counts.append({
                    'doc': item.get_name(),
                    'count': len(img_tags)
                })

    print(f"Documents with images: {len(doc_image_counts)}")
    total_imgs = sum(d['count'] for d in doc_image_counts)
    print(f"Total images referenced in HTML: {total_imgs}\n")

    if doc_image_counts:
        print("Images per document (showing docs with most images):")
        for doc in sorted(doc_image_counts, key=lambda x: x['count'], reverse=True)[:15]:
            print(f"  {doc['doc']}: {doc['count']} images")

if __name__ == '__main__':
    count_images_per_doc("/Volumes/T7 Shield/rag/books/epub/kotronias_0000_the_safest_scandinavian_reloaded.epub")
    count_images_per_doc("/Volumes/T7 Shield/rag/books/epub/john_2012_play_the_french_everyman_chess.epub")
    count_images_per_doc("/Volumes/T7 Shield/rag/books/epub/simeonidis_2020_carlsens_neo_moller_nic.epub")
