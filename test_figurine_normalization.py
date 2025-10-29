#!/usr/bin/env python3
"""
Test Figurine Normalization on Sample Books
Extracts text and tests figurine conversion.
"""

import sys
from pathlib import Path

from fast_epub_analyzer import extract_ebook_text_and_html
from figurine_normalizer import normalize_figurines, has_figurines, count_figurines


def test_book(epub_path: str):
    """Test figurine normalization on a single book."""
    filename = Path(epub_path).name
    print(f"\n{'='*80}")
    print(f"📖 Testing: {filename}")
    print(f"{'='*80}\n")

    # Extract text
    text, html, error = extract_ebook_text_and_html(epub_path)

    if error:
        print(f"❌ Extraction failed: {error}")
        return

    # Check for figurines
    has_figs = has_figurines(text)
    print(f"Contains figurines: {has_figs}")

    if has_figs:
        fig_counts = count_figurines(text)
        print(f"Figurine counts: {fig_counts}")
        print(f"Total figurines: {sum(fig_counts.values())}\n")

        # Show sample with figurines
        # Find first chunk with figurines
        sample_with_figs = None
        for i in range(0, len(text) - 500, 100):
            chunk = text[i:i+500]
            if has_figurines(chunk):
                sample_with_figs = chunk
                break

        if sample_with_figs:
            print("📄 BEFORE Normalization (first 500 chars with figurines):")
            print("-" * 80)
            print(sample_with_figs)
            print("-" * 80)
            print()

            normalized = normalize_figurines(sample_with_figs)
            print("✅ AFTER Normalization:")
            print("-" * 80)
            print(normalized)
            print("-" * 80)
            print()

            # Show conversion table
            print("Conversions detected:")
            for fig, count in fig_counts.items():
                print(f"   {fig} → {normalize_figurines(fig)} ({count} occurrences)")
        else:
            print("⚠️  Figurines found but not in first searchable chunks")
    else:
        print("ℹ️  No figurines found in this book")
        print()
        print("📄 Text sample (first 300 chars):")
        print("-" * 80)
        print(text[:300])
        print("-" * 80)


def main():
    """Test figurine normalization on sample books."""
    print("=" * 80)
    print("FIGURINE NORMALIZATION TEST")
    print("=" * 80)

    # Test books likely to have figurines
    test_books = [
        # Kasparov - likely has figurines
        "/Volumes/T7 Shield/epub/garry_2011_garry_kasparov_on_my_great_predecessors_part_4_everyman_chess.epub",
        # Tal - likely has figurines
        "/Volumes/T7 Shield/epub/mikhail_2012_the_life_and_games_of_mikhail_tal_everyman_chess.epub",
        # Study with Tal
        "/Volumes/T7 Shield/epub/unknown_author_0000_study_chess_with_tal.epub",
    ]

    found = 0
    total_tested = 0

    for book_path in test_books:
        if Path(book_path).exists():
            test_book(book_path)
            found += 1
        else:
            print(f"\n⚠️  Not found: {Path(book_path).name}")
        total_tested += 1

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Books tested: {total_tested}")
    print(f"Books found: {found}")
    print("=" * 80)


if __name__ == '__main__':
    main()
